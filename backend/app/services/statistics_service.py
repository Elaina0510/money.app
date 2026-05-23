"""Statistics business logic."""

from typing import Any

from sqlmodel import select, func, text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.record import Record
from app.models.tag import Tag
from app.models.category import Category


async def get_summary(
    db: AsyncSession,
    period: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Get income/expense summary for a given period.
    Uses consume_time for date filtering (v1.1).
    """
    # Adjust end_date to include full day
    end_filter = end_date + " 23:59" if len(end_date) <= 10 else end_date

    query = select(
        func.coalesce(
            func.sum(Record.amount).filter(Record.type == "income"), 0.0
        ).label("total_income"),
        func.coalesce(
            func.sum(Record.amount).filter(Record.type == "expense"), 0.0
        ).label("total_expense"),
        func.count(Record.id).label("transaction_count"),
    ).where(Record.consume_time >= start_date, Record.consume_time <= end_filter)

    result = await db.exec(query)
    row = result.one()
    total_income = float(row[0] if row[0] is not None else 0)
    total_expense = float(row[1] if row[1] is not None else 0)
    transaction_count = row[2] or 0

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": total_income - total_expense,
        "transaction_count": transaction_count,
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
    }


async def get_category_stats(
    db: AsyncSession,
    type_filter: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Get expense statistics by category."""
    end_filter = end_date + " 23:59" if len(end_date) <= 10 else end_date

    # Get total for percentage calculation
    total_stmt = select(
        func.coalesce(func.sum(Record.amount), 0.0).label("total")
    ).where(
        Record.type == type_filter,
        Record.consume_time >= start_date,
        Record.consume_time <= end_filter,
    )
    total_result = await db.exec(total_stmt)
    total_amount = float(total_result.one() or 0)

    # Get per-category stats
    stmt = (
        select(
            Record.category_id,
            func.coalesce(func.sum(Record.amount), 0.0).label("total"),
            func.count(Record.id).label("count"),
        )
        .where(
            Record.type == type_filter,
            Record.consume_time >= start_date,
            Record.consume_time <= end_filter,
        )
        .group_by(Record.category_id)
        .order_by(func.sum(Record.amount).desc())
    )
    result = await db.exec(stmt)
    rows = result.all()

    items = []
    for row in rows:
        category_id = row[0]
        total_val = float(row[1] or 0)
        count_val = row[2] or 0
        category = await db.get(Category, category_id)
        category_name = category.name if category else "未知"
        icon = category.icon if category else "mdi-cash"
        percentage = round((total_val / total_amount * 100), 1) if total_amount > 0 else 0
        items.append({
            "category_id": category_id,
            "category_name": category_name,
            "icon": icon,
            "total": total_val,
            "percentage": percentage,
            "count": count_val,
        })

    return {"items": items, "total_expense": total_amount}


async def get_tag_stats(
    db: AsyncSession,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Get statistics by tag (v1.1: single tag per record)."""
    end_filter = end_date + " 23:59" if len(end_date) <= 10 else end_date

    stmt = (
        select(
            Tag.name,
            func.coalesce(func.sum(Record.amount), 0.0).label("total"),
            func.count(Record.id).label("count"),
        )
        .join(Tag, Record.tag_id == Tag.id, isouter=True)
        .where(
            Record.consume_time >= start_date,
            Record.consume_time <= end_filter,
            Record.tag_id.isnot(None),
        )
        .group_by(Tag.name)
        .order_by(func.sum(Record.amount).desc())
    )
    result = await db.exec(stmt)
    rows = result.all()

    items = [
        {
            "tag_name": tag_name,
            "total": float(total or 0),
            "count": count or 0,
        }
        for tag_name, total, count in rows
    ]

    return {"items": items}


async def get_trend(
    db: AsyncSession,
    group_by: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Get income/expense trend grouped by day, week, month, or year."""
    end_filter = end_date + " 23:59" if len(end_date) <= 10 else end_date

    # Build date format string for SQLite
    if group_by == "year":
        date_format = "%Y"
    elif group_by == "month":
        date_format = "%Y-%m"
    elif group_by == "week":
        date_format = "%Y-%W"
    else:  # day
        date_format = "%Y-%m-%d"

    stmt = (
        select(
            func.strftime(date_format, Record.consume_time).label("period"),
            func.coalesce(
                func.sum(Record.amount).filter(Record.type == "income"), 0.0
            ).label("income"),
            func.coalesce(
                func.sum(Record.amount).filter(Record.type == "expense"), 0.0
            ).label("expense"),
        )
        .where(Record.consume_time >= start_date, Record.consume_time <= end_filter)
        .group_by(text("period"))
        .order_by(text("period"))
    )
    result = await db.exec(stmt)
    rows = result.all()

    items = [
        {
            "period": period,
            "income": float(income or 0),
            "expense": float(expense or 0),
            "balance": float(income or 0) - float(expense or 0),
        }
        for period, income, expense in rows
    ]

    return {"items": items}


async def get_compare(
    db: AsyncSession,
    start_date_1: str,
    end_date_1: str,
    start_date_2: str,
    end_date_2: str,
) -> dict[str, Any]:
    """Compare income/expense between two periods."""
    summary_1 = await get_summary(db, "custom", start_date_1, end_date_1)
    summary_2 = await get_summary(db, "custom", start_date_2, end_date_2)

    income_change = 0.0
    expense_change = 0.0

    if summary_1["total_income"] > 0:
        income_change = round(
            (summary_2["total_income"] - summary_1["total_income"])
            / summary_1["total_income"]
            * 100,
            1,
        )
    elif summary_2["total_income"] > 0:
        income_change = 100.0

    if summary_1["total_expense"] > 0:
        expense_change = round(
            (summary_2["total_expense"] - summary_1["total_expense"])
            / summary_1["total_expense"]
            * 100,
            1,
        )
    elif summary_2["total_expense"] > 0:
        expense_change = 100.0

    return {
        "period_1": {
            "total_income": summary_1["total_income"],
            "total_expense": summary_1["total_expense"],
        },
        "period_2": {
            "total_income": summary_2["total_income"],
            "total_expense": summary_2["total_expense"],
        },
        "income_change": income_change,
        "expense_change": expense_change,
    }
