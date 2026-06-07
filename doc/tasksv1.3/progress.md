# Money App v1.3 总体进度

> 建议开发顺序：1 → 4 → 6 → 2 → 3 → 5

## 模块完成状态

- [x] [模块 1：记账页返回时未保存提醒](record-form-leave-guard.md) — 优先级：高，复杂度：低
- [x] [模块 4：分类图标替代收支图标](category-icon.md) — 优先级：低，复杂度：低
- [x] [模块 6：宽屏适配 110% 放大](wide-screen-scale.md) — 优先级：低，复杂度：低
- [x] [模块 2：日历组件风格升级与动画](calendar-upgrade.md) — 优先级：中，复杂度：中
- [x] [模块 3：账单详情展开动画](record-detail-animation.md) — 优先级：中，复杂度：中
- [x] [模块 5：页面滑动模糊渐变](scroll-blur-gradient.md) — 优先级：中，复杂度：中

## 依赖关系

```
模块 1（返回提醒）── 独立，无依赖
模块 4（分类图标）── 独立，无依赖
模块 6（宽屏放大）── 独立，无依赖
模块 2（日历动画）── 新增 ExpandTransition.vue
模块 3（详情动画）── 依赖 ExpandTransition.vue（可选）、useAppStore 扩展
模块 5（模糊渐变）── 独立，涉及全局样式，建议最后实施
```

## 公共依赖

| 依赖 | 依赖方 | 说明 |
|------|--------|------|
| `ExpandTransition.vue`（新增） | 模块 2、模块 3 | 通用 expand 动画过渡组件 |
| `useAppStore.transitionOrigin`（新增） | 模块 3 | 路由过渡坐标传递 |

## 统计

- 总模块数：6
- 已完成：6 / 6
- 总子任务数：56
- 已完成：56 / 56

## 测试结果

- 测试文件：6 个
- 测试用例：65 个
- 通过率：100%

## 代码质量

- ESLint：通过
- Prettier：通过
- Vitest：全部通过
