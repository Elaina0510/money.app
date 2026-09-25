"""Tests for M1: CSV 识别层（解码 / 行矩阵 / 表头定位 / 方言 / 列角色）。

对应任务文件 §8.1–§8.8（用例名前缀即条目编号）与 §7 边界逐条。
以纯函数级为主；仅 §8.1「真实 BOM 闭环」与 §8.8 预览契约走 service / HTTP 层。
所有数据行均为**合成**值，不含任何真实账单数据（红线 11）。

v1.4.4 V2 翻案（推翻 boot3 D9 的两处局部口径，其余 D 决策继续有效）：
`交易对方` 从 `tag` 改判 `note`、`交易类型` 登记为 `category`；`note` 成为
「每角色一列」规则的唯一例外（可多列并存，见 §8.6 新增用例）。
"""

import inspect
import io
import zipfile

import pytest
from httpx import AsyncClient

from app.services.csv_dialects import (
    ALIPAY,
    CASHEW,
    CASHEW_TEMPLATE,
    COLUMN_ALIASES,
    DIALECT_ORDER,
    NATIVE,
    REQUIRED_ROLES,
    ROLES,
    WECHAT,
    dialects_in_order,
    locate_header_rows,
    match_dialect,
    normalize_header,
    resolve_columns,
)
from app.services.import_service import (
    csv_rows,
    detect_and_decode,
    detect_csv_format,
    preview_csv,
)

# ── 表头原文夹具（逐字取自设计 §0.4-10；数据行一律合成） ────────────────

NATIVE_HEADER = "amount,type,category_name,tag_name,consume_time,note"
CASHEW_HEADER = (
    "title,category name,amount,income,note,date,subcategory name,account,currency,wallet"
)
CASHEW_TEMPLATE_HEADER = "Date,Amount,Category,Title,Note,Account"
ALIPAY_HEADER = (
    "交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,"
    "收/付款方式,交易状态,交易订单号,商家订单号,备注,"
)
WECHAT_HEADER = (
    "交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,交易单号,商户单号,备注"
)


def _split(header_line: str) -> list[str]:
    """表头原文按逗号切成单元格（保留末尾空列）。"""
    return header_line.split(",")


def _wechat_leading(note_count: int = 4) -> list[list[str]]:
    """微信前导块（一手实测结构镜像：单格元信息 / 单格汇总 / `注：` + 编号注释 / 单格分隔线）。

    4 条编号注释 → 17 行（一手真实 xlsx 实测）；3 条 → 16 行（调研 CSV 样本）。
    """
    rows: list[list[str]] = [
        ["微信支付账单明细"],
        ["微信昵称：[测试昵称]"],
        ["起始时间：[2024-01-01 00:00:00] 终止时间：[2024-01-31 23:59:59]"],
        ["导出类型：[全部]"],
        ["导出时间：[2024-02-01 10:00:00]"],
        [""],
        ["共228笔记录"],
        ["收入：48笔 100.00元"],
        ["支出：176笔 200.00元"],
        ["中性交易：4笔 0.00元"],
        ["注："],
    ]
    rows += [[f"{i}. 本行为合成测试说明，不含真实数据"] for i in range(1, note_count + 1)]
    rows += [[""], ["----微信支付账单明细列表----"]]
    return rows


def _alipay_leading(extra: int = 0) -> list[list[str]]:
    """支付宝前导块（一手实测：前导 24 行，元信息与汇总均为**单格**行 → 评分 0）。"""
    rows: list[list[str]] = [
        ["支付宝交易明细对账单"],
        ["账号：[test@example.com]"],
        ["起始日期：[2024-01-01 00:00:00]    终止日期：[2024-01-31 23:59:59]"],
        ["导出时间：2024-02-01 10:00:00"],
        [""],
    ]
    rows += [[f"说明 {i}：本行为合成测试前导说明"] for i in range(1, 16 + extra)]
    rows += [
        ["--------收入支出汇总--------"],
        ["共30笔收入，合计100.00元"],
        ["共180笔支出，合计200.00元"],
        ["--------交易明细列表--------"],
    ]
    return rows


def _wechat_data() -> list[list[str]]:
    return [
        [
            "2024-01-15 12:00:00", "商户消费", "某商家", "外卖订单", "支出", "¥28.16",
            "零钱", "支付成功", "4200000000", "/", "/",
        ],
        [
            "2024-01-16 09:30:00", "转账", "张三", "", "收入", "¥100.00",
            "零钱", "已到账", "4200000001", "/", "/",
        ],
        [
            "2024-01-17 10:00:00", "零钱提现", "", "", "支出", "¥9.78",
            "零钱", "已退款¥9.78", "4200000002", "/", "/",
        ],
    ]


def _wechat_matrix(leading_rows: int = 17) -> list[list[str]]:
    leading = _wechat_leading(4 if leading_rows == 17 else 3)
    assert len(leading) == leading_rows
    return leading + [_split(WECHAT_HEADER)] + _wechat_data()


def _alipay_matrix(extra: int = 0) -> list[list[str]]:
    leading = _alipay_leading(extra)
    return leading + [_split(ALIPAY_HEADER)] + [
        [
            "2024-01-15 12:00", "餐饮", "某商家", "180***0000", "外卖", "支出", "28.16",
            "支付宝", "交易成功", "T1", "M1", "/", "",
        ]
    ]


# ── 8.1 BOM 闭环（需求 D 的钉子） ──────────────────────────────────


class Test81BomClosedLoop:
    """自家带 BOM 的导出必须能识别回 `native`。"""

    async def test_8_1_real_export_bytes_roundtrip(
        self, auth_client: AsyncClient, db_session
    ) -> None:
        """取 `export_csv` 的**真实产物字节**走完整识别链（非手写无 BOM 串）。"""
        cat_resp = await auth_client.post(
            "/api/categories",
            json={"name": "餐饮", "type": "expense", "icon": "mdi-food", "sort_order": 1},
        )
        cat_id = cat_resp.json()["data"]["id"]
        for consume_time in ("2024-01-15 12:00", "2024-01-16 12:00"):
            resp = await auth_client.post(
                "/api/records",
                json={
                    "amount": 50.0,
                    "type": "expense",
                    "category_id": cat_id,
                    "consume_time": consume_time,
                    "note": "测试账单",
                },
            )
            assert resp.status_code == 200

        raw = (await auth_client.get("/api/export/csv")).content
        assert raw[:3] == b"\xef\xbb\xbf"  # 真实 BOM 字节

        text, encoding = detect_and_decode(raw)
        assert encoding == "utf-8-sig"
        assert not text.startswith("\ufeff")
        rows = csv_rows(text)
        assert rows[0][0] == "amount"  # 旧实现此处为 "\ufeffamount" → 整文件被拒
        assert detect_csv_format(rows[0]) == "native"

        result = await preview_csv(db_session, raw)
        assert result["format"] == "native"
        assert result["encoding"] == "utf-8-sig"
        assert result["headers"] == _split(NATIVE_HEADER)
        assert result["row_count"] == 2
        assert result["categories_in_file"] == ["餐饮"]

    def test_8_1_handwritten_bom_prefix_bytes(self) -> None:
        """手写 `\\xef\\xbb\\xbf` 前缀字节：BOM 不得残留在首列表头。"""
        body = NATIVE_HEADER + "\n50.0,expense,餐饮,午餐,2024-01-15 12:00,测试\n"
        raw = b"\xef\xbb\xbf" + body.encode("utf-8")
        assert raw[:3] == b"\xef\xbb\xbf"
        text, encoding = detect_and_decode(raw)
        assert encoding == "utf-8-sig"
        assert "\ufeff" not in text
        assert detect_csv_format(csv_rows(text)[0]) == "native"

    def test_8_1_bom_stripped_before_alias_lookup(self) -> None:
        """BOM 剥除后中文表头照常命中别名（步骤 1 的兜底意义）。"""
        raw = ("\ufeff金额,交易时间\n1,2024-01-01\n").encode("utf-8")
        text, _encoding = detect_and_decode(raw)
        assert text.startswith("金额")
        headers = csv_rows(text)[0]
        assert headers[0] == "金额"
        assert [h.role for h in resolve_columns(headers, None)] == ["amount", "consume_time"]
        assert detect_csv_format(headers) == "custom"


# ── 8.2 normalize_header 逐形态（D4 五步，顺序不可换） ──────────────


class Test82NormalizeHeader:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("\ufeffamount", "amount"),              # 步骤 1：剥 BOM
            ("ＤＡＴＥ", "date"),                         # 步骤 2：NFKC 全角字母
            ("金额２", "金额2"),                             # 步骤 2：NFKC 全角数字
            ("金额（元）", "金额"),                            # 步骤 2+4：全角括号在 NFKC 后才可剥
            ("\t金额\u3000", "金额"),                        # 步骤 3：TAB 与全角空格两端
            ("  Category Name  ", "category name"),          # 步骤 3+5
            ("金额(元)", "金额"),                             # 步骤 4：剥结尾半角括号单位
            ("金额 （元）", "金额"),                           # 步骤 4：括号前空白一并剥
            ("收入(含税)(元)", "收入(含税)"),                  # 只剥「单位」，非单位括号保留
            ("金额(元)(元)", "金额"),                           # 一次剥净单位链 → 幂等
            ("商品(说明)", "商品(说明)"),                        # 非单位结尾括号不误伤
            ("金额(人民币)", "金额"),                            # 中文单位
            ("Amount (USD)", "amount"),                        # 拉丁单位
            ("收/支", "收/支"),                              # 斜杠列名原样
            ("交易  时间", "交易 时间"),                       # 内部连续空白折叠为单空格
            ("CATEGORY  NAME", "category name"),             # 折叠 + lower
            ("", ""),
            ("   ", ""),
        ],
    )
    def test_8_2_forms(self, raw: str, expected: str) -> None:
        assert normalize_header(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "\ufeffamount", "ＤＡＴＥ", "金额（元）", "  Category  Name ", "\t备注\u3000",
            "收入(含税)(元)", "收/支", "category name", "", "(元)",
        ],
    )
    def test_8_2_idempotent(self, raw: str) -> None:
        once = normalize_header(raw)
        assert normalize_header(once) == once

    def test_8_2_empty_header_never_lands_a_key(self) -> None:
        """空列名归一为 `""`，且不落别名表、不落任何方言 roles（M1 §2.2）。"""
        assert normalize_header("  \ufeff ") == ""
        assert "" not in COLUMN_ALIASES
        for dialect in dialects_in_order():
            assert "" not in dialect.roles

    def test_8_2_alias_table_is_a_closed_set(self) -> None:
        """别名表逐键钉死（v1.4.4 V2 翻案后）：`交易类型` 登记为 category、`交易对方` 改判 note。

        原 D9 的「`交易类型` 故意不登记」已被 V2 推翻；`金额(元)` 仍不重复登记（D4）。
        """
        assert len(COLUMN_ALIASES) == 22
        assert COLUMN_ALIASES["交易类型"] == "category", "V2：微信分类来源就是这一列"
        assert COLUMN_ALIASES["交易对方"] == "note", "V2：交易对方进备注、不再建标签"
        assert "tag" in set(COLUMN_ALIASES.values()), "tag 角色仍有内置别名（native/cashew 的列名）"
        assert "金额(元)" not in COLUMN_ALIASES
        assert set(COLUMN_ALIASES.values()) == set(ROLES)


# ── 8.3 locate_header_rows（入参是**行矩阵**，§4.1） ─────────────────


class Test83LocateHeaderRows:
    def test_8_3_wechat_17_leading_rows(self) -> None:
        rows = _wechat_matrix(17)
        index, headers, data_rows = locate_header_rows(rows)
        assert index == 17
        assert headers[:3] == ["交易时间", "交易类型", "交易对方"]
        assert headers[5] == "金额"  # `金额(元)` 归一后落 `金额`（D4）
        assert len(data_rows) == 3
        assert data_rows[0][0].startswith("2024-01-15")

    def test_8_3_wechat_16_leading_rows(self) -> None:
        """一手 xlsx 17 行 vs 调研 CSV 16 行：同一函数两形态均命中（D1 禁止 skiprows）。"""
        index, _headers, data_rows = locate_header_rows(_wechat_matrix(16))
        assert index == 16
        assert len(data_rows) == 3

    def test_8_3_alipay_24_leading_rows(self) -> None:
        rows = _alipay_matrix()
        assert len(_alipay_leading()) == 24
        index, headers, data_rows = locate_header_rows(rows)
        assert index == 24
        assert len(headers) == 13
        assert headers[-1] == ""  # 末尾多一个逗号 = 第 13 个空列
        assert len(data_rows) == 1

    def test_8_3_two_more_leading_rows_still_hits(self) -> None:
        """再插 2 行说明仍命中正确表头（前导行数必然漂移）。"""
        index, headers, _data = locate_header_rows(_alipay_matrix(extra=2))
        assert index == 26
        assert headers[1] == "交易分类"

    def test_8_3_max_scan_window(self) -> None:
        rows = [[f"说明{i}：" + "0" * 8] for i in range(3)] + [_split(NATIVE_HEADER)]
        assert locate_header_rows(rows)[0] == 3
        for too_small in (2, 3):
            with pytest.raises(ValueError, match="CSV 文件为空"):
                locate_header_rows(rows, max_scan=too_small)

    def test_8_3_degrade_when_every_score_is_zero(self) -> None:
        """全 0 分 → 退化为「首个非空单元格 ≥2 的行」（D2 全手动场景）。"""
        rows = [["col1", "col2", "col3"], ["a", "b", "c"]]
        index, headers, data_rows = locate_header_rows(rows)
        assert index == 0
        assert headers == ["col1", "col2", "col3"]
        assert data_rows == [["a", "b", "c"]]

    def test_8_3_single_cell_rows_excluded_by_both_criteria(self) -> None:
        """单非空格前导行被双判据排除：评分 0 且「非空单元格 ≥2」不满足（§7.4）。"""
        rows = [["注：本文件没有表头"], ["----分隔线----"], [""], ["共10笔记录"]]
        with pytest.raises(ValueError, match="CSV 文件为空"):
            locate_header_rows(rows)

    def test_8_3_empty_and_blank_only_input(self) -> None:
        for rows in ([], [[""], [""]], [[]], [["", "  "]]):
            with pytest.raises(ValueError, match="CSV 文件为空"):
                locate_header_rows(rows)

    def test_8_3_tie_prefers_earlier_row(self) -> None:
        rows = [_split(NATIVE_HEADER), _split(NATIVE_HEADER)]
        index, _headers, data_rows = locate_header_rows(rows)
        assert index == 0
        assert len(data_rows) == 1

    def test_8_3_leading_rows_dropped_from_data(self) -> None:
        """前导行整体丢弃、不计入数据行（§4.6）。"""
        _index, _headers, data_rows = locate_header_rows(_wechat_matrix(17))
        flat = [cell for row in data_rows for cell in row]
        assert "----微信支付账单明细列表----" not in flat
        assert "共228笔记录" not in flat
        assert len(data_rows) == 3


# ── 8.3b csv_rows（D27 的 CSV 半边） ───────────────────────────────


class Test83bCsvRows:
    def test_8_3b_row_matrix_positional(self) -> None:
        text = 'amount,note\n1.5,"a,b"\n2,中文\n'
        assert csv_rows(text) == [["amount", "note"], ["1.5", "a,b"], ["2", "中文"]]

    def test_8_3b_empty_text_is_empty_matrix(self) -> None:
        assert csv_rows("") == []

    def test_8_3b_crlf_matches_lf(self) -> None:
        """CRLF 行尾（支付宝/微信导出的实际形态）与 LF 结果逐格一致。"""
        assert csv_rows("a,b\r\nc,d\r\n") == csv_rows("a,b\nc,d\n") == [["a", "b"], ["c", "d"]]

    async def test_8_3b_single_column_preview_warns_not_rejects(self) -> None:
        """设计 §1.3「单列文件（只有 Amount）」：只 warning，不拒绝（确认阶段才由 M3 拒）。"""
        result = await preview_csv(None, b"amount\r\n50")  # type: ignore[arg-type]  # 无分类值 → 不触库
        assert result["format"] == "custom"
        assert result["row_count"] == 1
        assert [c["role"] for c in result["columns"]] == ["amount"]
        assert any("缺少必需列：交易时间" in w for w in result["warnings"])
        assert result["suggested_type_source"] == "sign"

    def test_8_3b_bare_cr_becomes_chinese_value_error(self) -> None:
        """裸换行内容 → 中文 ValueError；英文 `_csv.Error` 文案不得外泄。"""
        with pytest.raises(ValueError, match="CSV 文件内容为空或格式不正确") as exc:
            csv_rows("a\rb,c\nd,e")
        assert "new-line character" not in str(exc.value)
        assert type(exc.value) is ValueError  # 不是 csv.Error 的子类冒上去

    def test_8_3b_binary_like_text_no_english_error_leaks(self) -> None:
        """zip 字节流经 `detect_and_decode` 后不得把英文内部异常冒到调用方。"""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("[Content_Types].xml", "<Types>a\rb\rc\rd\x00")
            zf.writestr("xl/worksheets/sheet1.xml", "<row>a\rb\x00c")
        text, _encoding = detect_and_decode(buffer.getvalue())
        with pytest.raises(ValueError) as exc:
            csv_rows(text)
        assert str(exc.value) == "CSV 文件内容为空或格式不正确"


# ── 8.4 detect_csv_format：五方言 + custom + D5 顺序陷阱 ─────────────


class Test84DetectCsvFormat:
    @pytest.mark.parametrize(
        ("header_line", "expected"),
        [
            (NATIVE_HEADER, "native"),
            (CASHEW_HEADER, "cashew"),
            (CASHEW_TEMPLATE_HEADER, "cashew_template"),
            (ALIPAY_HEADER, "alipay"),
            (WECHAT_HEADER, "wechat"),
        ],
    )
    def test_8_4_five_dialects(self, header_line: str, expected: str) -> None:
        assert detect_csv_format(_split(header_line)) == expected

    def test_8_4_unknown_headers_fall_to_custom_without_raising(self) -> None:
        assert detect_csv_format(_split("col1,col2,col3")) == "custom"
        assert detect_csv_format(["随手记", "京东金融", "招行流水"]) == "custom"
        assert detect_csv_format([]) == "custom"

    def test_8_4_closed_set_of_keys_and_chinese_labels(self) -> None:
        assert [d.key for d in dialects_in_order()] == list(DIALECT_ORDER)
        assert set(DIALECT_ORDER) == {"native", "cashew", "cashew_template", "alipay", "wechat"}
        assert {d.label for d in dialects_in_order()} == {
            "本系统格式", "Cashew 全量导出", "Cashew 导入模板", "支付宝账单", "微信账单",
        }

    def test_8_4_d5_alipay_must_precede_wechat(self) -> None:
        """D5 顺序陷阱：支付宝表头必须判 `alipay`；乱序即误判并**丢分类列**。"""
        alipay_headers = _split(ALIPAY_HEADER)
        assert DIALECT_ORDER.index("alipay") < DIALECT_ORDER.index("wechat")
        assert detect_csv_format(alipay_headers) == "alipay"

        # 测试内局部乱序（不改生产常量）：wechat 在前 → 支付宝被判成 wechat
        wrong_order = ("native", "cashew", "cashew_template", "wechat", "alipay")
        assert match_dialect(alipay_headers, order=wrong_order) is WECHAT
        lost = [h.role for h in resolve_columns(alipay_headers, WECHAT)]
        assert "category" not in lost          # 交易分类列被丢 → 用户只剩「无分类列」
        assert lost[1] is None
        # 反向证据：微信表头不会被更严的支付宝判据抢走
        assert match_dialect(_split(WECHAT_HEADER)) is WECHAT

    def test_8_4_dialect_type_source_and_roles_domains(self) -> None:
        for dialect in dialects_in_order():
            assert set(dialect.roles.values()) <= set(ROLES)
            assert dialect.type_source in ("column", "sign", "all_expense", "all_income")
        assert CASHEW_TEMPLATE.type_source == "sign"
        assert {
            NATIVE.type_source, CASHEW.type_source, ALIPAY.type_source, WECHAT.type_source
        } == {"column"}


# ── 8.5 native 严格集合相等不破（且不再拒绝） ───────────────────────


class Test85NativeStrictEquality:
    def test_8_5_exact_set_is_native(self) -> None:
        assert detect_csv_format(_split(NATIVE_HEADER)) == "native"

    def test_8_5_missing_column_is_custom_not_reject(self) -> None:
        assert detect_csv_format(
            ["amount", "type", "category_name", "tag_name", "consume_time"]
        ) == "custom"

    def test_8_5_extra_column_is_custom(self) -> None:
        assert detect_csv_format(_split(NATIVE_HEADER) + ["extra"]) == "custom"

    def test_8_5_renamed_column_is_custom(self) -> None:
        assert detect_csv_format(
            ["amount", "type", "分类", "tag_name", "consume_time", "note"]
        ) == "custom"

    def test_8_5_reordered_native_still_native(self) -> None:
        assert detect_csv_format(
            ["note", "amount", "consume_time", "type", "tag_name", "category_name"]
        ) == "native"


# ── 8.6 resolve_columns：逐列角色 / 冲突 / 样例值 ───────────────────


class Test86ResolveColumns:
    def test_8_6_wechat_all_eleven_columns(self) -> None:
        headers = _split(WECHAT_HEADER)
        hints = resolve_columns(headers, WECHAT, _wechat_data())
        assert [h.index for h in hints] == list(range(11))
        assert [h.header for h in hints] == headers  # 原样（仅两端去空白，保留大小写）
        # v1.4.4 V2：`交易类型`→category（微信分类来源）、`交易对方`→note（不再是 tag）
        assert [h.role for h in hints] == [
            "consume_time", "category", "note", "note", "type", "amount",
            None, None, None, None, None,
        ]
        # note 多列并存：两列都拿到角色、都不标冲突（V2 的「每角色一列」唯一例外）
        assert [h.conflict for h in hints] == [False] * 11
        assert hints[5].sample == "¥28.16"
        assert hints[10].sample == ""  # 备注列全为 `/` → 空占位（D31）
        assert hints[9].sample == ""   # 商户单号列同上

    def test_8_6_alipay_all_thirteen_columns(self) -> None:
        headers = _split(ALIPAY_HEADER)
        hints = resolve_columns(headers, ALIPAY, _alipay_matrix()[-1:])
        assert [h.role for h in hints] == [
            "consume_time", "category", "note", None, "note", "type", "amount",
            None, None, None, None, None, None,
        ]
        assert [h.conflict for h in hints] == [False] * 13, "V2：note 两列并存不判冲突"
        assert hints[11].header == "备注"
        assert hints[11].role is None  # `备注` 未登记进 ALIPAY.roles（V2 未扩这一列，仍丢弃）
        assert not hints[11].conflict, "未登记 ≠ 冲突：它压根没参与角色竞争"
        assert hints[12].header == ""
        assert hints[12].role is None  # §7.2 空尾列天然丢弃，不计入任何集

    def test_8_6_note_is_the_only_multi_column_role(self) -> None:
        """V2 的边界：`note` 可多列命中，其余角色仍「先列独占」（D3 未被整体放宽）。"""
        hints = resolve_columns(["交易对方", "商品", "金额", "金额"], None)
        assert [h.role for h in hints] == ["note", "note", "amount", None]
        assert [h.conflict for h in hints] == [False, False, False, True]
        # 同一规则对方言路径同样成立（微信 roles 里两列都写 note）
        wechat = resolve_columns(_split(WECHAT_HEADER), WECHAT)
        assert [h.header for h in wechat if h.role == "note"] == ["交易对方", "商品"]

    def test_8_6_cashew_roles_migrated_from_dead_constant(self) -> None:
        assert [h.role for h in resolve_columns(_split(CASHEW_HEADER), CASHEW)] == [
            "tag", "category", "amount", "type", "note", "consume_time",
            None, None, None, None,
        ]

    def test_8_6_native_roles_are_six_same_named(self) -> None:
        assert [h.role for h in resolve_columns(_split(NATIVE_HEADER), NATIVE)] == [
            "amount", "type", "category", "tag", "consume_time", "note",
        ]

    def test_8_6_conflict_takes_earlier_column(self) -> None:
        hints = resolve_columns(["金额", "金额", "交易时间"], None)
        assert [h.role for h in hints] == ["amount", None, "consume_time"]
        assert [h.conflict for h in hints] == [False, True, False]

    def test_8_6_without_dialect_uses_alias_table(self) -> None:
        assert [h.role for h in resolve_columns(["日期", "花费", "备注"], None)] == [
            "consume_time", None, "note",
        ]

    def test_8_6_sample_skips_blank_and_placeholder(self) -> None:
        data = [["", "/"], ["/", " x\t "], ["v", "real"]]
        hints = resolve_columns(["a", "b"], None, data)
        assert hints[0].sample == "v"
        assert hints[1].sample == "x"

    def test_8_6_sample_empty_without_data_rows(self) -> None:
        assert [h.sample for h in resolve_columns(["金额"], None)] == [""]

    def test_8_6_empty_headers_raise(self) -> None:
        with pytest.raises(ValueError, match="CSV 文件为空"):
            resolve_columns([], None)

    def test_8_6_full_width_headers_hit_roles(self) -> None:
        assert [h.role for h in resolve_columns(["金额（元）", "ＤＡＴＥ"], None)] == [
            "amount", "consume_time",
        ]

    def test_8_6_roles_are_key_by_key_pinned(self) -> None:
        """五方言 roles 逐键钉死（D3/D30 + v1.4.4 V2），`ROLES`/`REQUIRED_ROLES` 为封闭集。"""
        assert set(NATIVE.roles) == set(NATIVE.required)
        assert set(CASHEW.roles) == {"title", "category name", "amount", "income", "note", "date"}
        assert set(CASHEW_TEMPLATE.roles) == {"date", "amount", "category", "title", "note"}
        assert set(ALIPAY.roles) == {
            "交易时间", "交易分类", "金额", "收/支", "交易对方", "商品说明",
        }
        assert set(WECHAT.roles) == {
            "交易时间", "交易类型", "金额", "收/支", "交易对方", "商品",
        }, "V2：微信新增 `交易类型→category`，`交易对方` 改判 note"
        # V2 的「两列同为 note」写在数据表里，而不是靠代码特例
        assert [r for r in ALIPAY.roles.values() if r == "note"] == ["note", "note"]
        assert [r for r in WECHAT.roles.values() if r == "note"] == ["note", "note"]
        assert ROLES == ("consume_time", "amount", "type", "category", "tag", "note")
        assert REQUIRED_ROLES == ("consume_time", "amount")


# ── 8.7 GB18030 中文表头字节流 ─────────────────────────────────────


class Test87Gb18030:
    def test_8_7_alipay_gb18030_decodes_and_matches(self) -> None:
        row = (
            "2024-01-15 12:00,餐饮,某商家,180***0000,外卖,支出,28.16,支付宝,交易成功,T,M,/,/"
        )
        body = ALIPAY_HEADER + "\n" + (row + "\n") * 8
        raw = body.encode("gb18030")
        with pytest.raises(UnicodeDecodeError):
            raw.decode("utf-8")  # 前置事实：不是 UTF-8

        text, encoding = detect_and_decode(raw)
        assert encoding.lower().replace("-", "") in {"gb18030", "gbk", "gb2312"}
        assert "交易时间" in text
        assert detect_csv_format(csv_rows(text)[0]) == "alipay"

    def test_8_7_gbk_bytes_are_covered_by_gb18030(self) -> None:
        row = (
            "2024-01-15 12:00,商户消费,张三,商品,支出,￥9.78,零钱,支付成功,4200000000,/,"
        )
        raw = (WECHAT_HEADER + "\n" + (row + "\n") * 8).encode("gbk")
        text, encoding = detect_and_decode(raw)
        assert encoding.lower().replace("-", "").startswith("gb")
        assert detect_csv_format(csv_rows(text)[0]) == "wechat"

    def test_8_7_invalid_tail_uses_replace_and_never_raises(self) -> None:
        """生僻字 / 非法尾字节走 `errors="replace"` 兜底，**不抛**（§1.3 已知边界）。"""
        raw = ("金额,交易时间\n1,2024-01-01\n" * 6).encode("gb18030") + b"\x80\x81\xff\xfe\xa1\xa2"
        text, encoding = detect_and_decode(raw)
        assert isinstance(text, str)
        assert text
        assert encoding

    async def test_8_7_preview_reports_decoding_label(self, db_session) -> None:
        row = "2024-01-15 12:00,餐饮,某商家,,外卖,支出,28.16,支付宝,成功,T,M,/,/"
        raw = (ALIPAY_HEADER + "\n" + (row + "\n") * 8).encode("gb18030")
        result = await preview_csv(db_session, raw)
        assert result["format"] == "alipay"
        assert result["encoding"].lower().replace("-", "") in {"gb18030", "gbk", "gb2312"}
        assert result["categories_in_file"] == ["餐饮"]


# ── 8.8 preview_csv 契约（既有 5 字段逐位回归 + 新 7 字段） ──────────


class Test88PreviewContract:
    async def test_8_8_native_regression_bitwise(self, db_session) -> None:
        """与改造前**逐位一致**：format / row_count / categories_in_file / tags_in_file。"""
        raw = (NATIVE_HEADER + "\n50.0,expense,餐饮,午餐,2024-01-15 12:00,测试").encode("utf-8")
        result = await preview_csv(db_session, raw)
        assert result["format"] == "native"
        assert result["row_count"] == 1
        assert result["categories_in_file"] == ["餐饮"]
        assert result["tags_in_file"] == ["午餐"]
        assert result["cache_id"]

    async def test_8_8_cashew_regression_bitwise(self, db_session) -> None:
        raw = (
            CASHEW_HEADER + "\n午餐,餐饮,-50.0,false,测试,2024-01-15 12:00:00.000,"
            "子分类,账户,人民币,钱包"
        ).encode("utf-8")
        result = await preview_csv(db_session, raw)
        assert result["format"] == "cashew"
        assert result["row_count"] == 1
        assert result["categories_in_file"] == ["餐饮"]
        assert result["tags_in_file"] == ["午餐"]

    async def test_8_8_seven_new_fields_shape(self, db_session) -> None:
        body = (
            NATIVE_HEADER + "\n50.0,expense,餐饮,午餐,2024-01-15 12:00,测试\n"
            "\n60.0,income,工资,奖金,2024-02-01 09:00,月薪"
        )
        result = await preview_csv(db_session, body.encode("utf-8"))
        assert result["headers"] == _split(NATIVE_HEADER)
        assert result["header_row_index"] == 0
        assert [set(c) for c in result["columns"]] == [{"index", "header", "role", "sample"}] * 6
        assert [c["role"] for c in result["columns"]] == [
            "amount", "type", "category", "tag", "consume_time", "note",
        ]
        assert result["columns"][0]["sample"] == "50.0"
        assert result["suggested_type_source"] == "column"
        assert result["encoding"] == "utf-8"
        assert result["sample_rows"] == [
            ["50.0", "expense", "餐饮", "午餐", "2024-01-15 12:00", "测试"],
            ["60.0", "income", "工资", "奖金", "2024-02-01 09:00", "月薪"],
        ]
        assert result["warnings"] == []
        assert result["row_count"] == 2  # 中间空行不计入
        assert result["container"] == "csv"  # 第 8 契约字段已由 M6 落地（原「缺席」断言到期，主 Agent 单点改写）
        # v1.4.4 的第 9 契约字段：键 = `categories_in_file` 同名值、值 = 命中的分类 id / None。
        # 本例两个名字都是 conftest 预置的预设分类 → 自动匹配（= 落库链同一函数）必命中。
        suggested = result["categories_suggested"]
        assert set(suggested) == set(result["categories_in_file"]) == {"餐饮", "工资"}
        assert all(isinstance(cid, int) for cid in suggested.values()), suggested

    async def test_8_8_three_warning_classes(self) -> None:
        """warnings 三类：前导行丢弃 / 无分类列 / 缺必需列（§6.4，全中文、无内部术语）。"""
        body = "微信支付账单明细\n注：合成说明\n交易时间,交易对方\n2024-01-15 12:00,张三"
        result = await preview_csv(None, body.encode("utf-8"))  # type: ignore[arg-type]
        assert result["format"] == "custom"
        assert result["header_row_index"] == 2
        assert result["warnings"] == [
            "已忽略表头前的 2 行说明文字",
            "未识别到分类列：需指定默认分类",
            "缺少必需列：金额",
        ]
        assert result["suggested_type_source"] == "sign"

    async def test_8_8_duplicate_column_warning(self) -> None:
        """§7.1 重复列名 → 靠前列得角色 + warnings。"""
        result = await preview_csv(
            None, "金额,金额,交易时间\n10,20,2024-01-01".encode()  # type: ignore[arg-type]
        )
        assert [c["role"] for c in result["columns"]] == ["amount", None, "consume_time"]
        assert result["warnings"][-1].startswith("多列对应同一角色")
        assert any("未识别到分类列" in w for w in result["warnings"])
        assert not any("缺少必需列" in w for w in result["warnings"])

    async def test_8_8_cashew_template_enters_preview(self, db_session) -> None:
        """用户发起本批的那份模板：不再报「无法识别」，且 `suggested_type_source == sign`。"""
        body = (
            CASHEW_TEMPLATE_HEADER + "\n"
            "2026-09-24 11:07:54.617083,-50,Groceries,Fruits and Vegetables,Paid with cash,\n"
            "2026-09-24 11:07:54.617085,250,Bills & Fees,Monthly Income,,"
        )
        result = await preview_csv(db_session, body.encode("utf-8"))
        assert result["format"] == "cashew_template"
        assert result["suggested_type_source"] == "sign"
        assert result["row_count"] == 2
        assert result["categories_in_file"] == ["Bills & Fees", "Groceries"]
        # 全不命中（库内无同名/包含/同义词分类）→ 值逐个为 None，前端即留「— 跳过 —」
        assert result["categories_suggested"] == {"Bills & Fees": None, "Groceries": None}
        assert result["columns"][5] == {"index": 5, "header": "Account", "role": None, "sample": ""}
        assert result["sample_rows"][0][1] == "-50"

    async def test_8_8_wechat_leading_rows_preview(self, db_session) -> None:
        """真实形态：前导 17 行微信表头进预览，`/` 不产生分类/标签（D31）。

        v1.4.4 V2 的预览侧后果：分类列来自 `交易类型`（`categories_in_file` 不再是空集），
        `交易对方` 改判 note → `tags_in_file` 为空（微信不再产生标签），
        「未识别到分类列：需指定默认分类」告警对真实微信账单**消失**。
        """
        text = "\n".join(",".join(row) for row in _wechat_matrix(17))
        result = await preview_csv(db_session, text.encode("utf-8"))
        assert result["format"] == "wechat"
        assert result["header_row_index"] == 17
        assert result["row_count"] == 3
        assert result["categories_in_file"] == ["商户消费", "转账", "零钱提现"]
        assert result["tags_in_file"] == [], "V2：微信无 tag 列（交易对方已并入备注）"
        # 三个交易类型都对不上预设分类 → 建议逐个 None（前端留「— 跳过 —」交后端链尾兜底）
        assert set(result["categories_suggested"]) == set(result["categories_in_file"])
        assert set(result["categories_suggested"].values()) == {None}
        assert "/" not in result["tags_in_file"]
        assert result["warnings"] == ["已忽略表头前的 17 行说明文字"]
        assert "未识别到分类列：需指定默认分类" not in result["warnings"]
        assert result["suggested_type_source"] == "column"
        assert result["sample_rows"][0][5] == "¥28.16"

    async def test_8_8_unknown_format_no_longer_rejected(self) -> None:
        """需求 A：无表头文件退化取表头并进预览（不抛异常、全列手选）。"""
        result = await preview_csv(None, b"1,2,3\n4,5,6")  # type: ignore[arg-type]
        assert result["format"] == "custom"
        assert result["header_row_index"] == 0
        assert result["headers"] == ["1", "2", "3"]
        assert all(c["role"] is None for c in result["columns"])
        assert result["row_count"] == 1

    async def test_8_8_only_header_rows(self) -> None:
        """§7.5 仅表头无数据行 → 正常返回、`row_count == 0`。"""
        result = await preview_csv(None, NATIVE_HEADER.encode("utf-8"))  # type: ignore[arg-type]
        assert result["row_count"] == 0
        assert result["sample_rows"] == []
        assert result["categories_in_file"] == []
        assert result["tags_in_file"] == []

    async def test_8_8_empty_file_keeps_existing_message(self) -> None:
        for empty in (b"", b"\n\n\n", b"\xef\xbb\xbf"):
            with pytest.raises(ValueError, match="CSV 文件为空"):
                await preview_csv(None, empty)  # type: ignore[arg-type]

    def test_8_8_legacy_rejection_message_is_gone(self) -> None:
        """旧拒绝文案「无法识别的 CSV 格式」随需求 A 自然消失，且不新增替代文案（U3）。"""
        from app.services import csv_dialects, import_service

        assert "无法识别的 CSV 格式" not in inspect.getsource(import_service)
        # 既有「CSV 文件为空」措辞保留，只是抛出点搬进定位函数（U3 / §4.5）
        assert "CSV 文件为空" in inspect.getsource(csv_dialects)
