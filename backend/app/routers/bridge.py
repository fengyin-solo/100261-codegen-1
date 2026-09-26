"""廊桥对接接口：维护廊桥，覆盖靠接廊桥、撤离廊桥、登记检修等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.bridge import BridgeService

router = APIRouter(prefix="/api/bridge", tags=["廊桥对接"])

service = BridgeService()

LIST_FIELDS = ["廊桥编号", "对应机位", "适用机型", "对接高度", "预靠时间", "撤桥时间", "操作人员", "廊桥状态"]
STATUSES = ["待靠接", "已靠接", "待撤离", "检修中"]


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按廊桥编号检索"),
    status: str | None = Query(default=None, description="待靠接、已靠接、待撤离、检修中"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按廊桥编号与状态过滤廊桥对接列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条廊桥明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"廊桥 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条廊桥，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="廊桥已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条廊桥执行靠接廊桥、撤离廊桥、登记检修；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出廊桥对接清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "bridge", "total": total, "items": items}
