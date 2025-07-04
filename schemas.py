from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DeviceBase(BaseModel):
    ip_address: str
    user: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    purpose: Optional[str] = None
    device_type: Optional[str] = None
    first_offline_time: Optional[datetime] = None  # 新增字段

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(DeviceBase):
    pass

class Device(DeviceBase):
    id: int

    class Config:
        from_attributes = True  # 替换 orm_mode = True