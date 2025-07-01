from sqlalchemy.orm import Session
import schemas
from database import Device

def get_device_by_ip(db: Session, ip_address: str):
    return db.query(Device).filter(Device.ip_address == ip_address).first()

def get_devices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Device).offset(skip).limit(limit).all()

def create_device(db: Session, device: schemas.DeviceCreate):
    db_device = Device(ip_address=device.ip_address, user=device.user, start_time=device.start_time, end_time=device.end_time, purpose=device.purpose)
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def update_device(db: Session, ip_address: str, device: schemas.DeviceUpdate):
    db_device = get_device_by_ip(db, ip_address)
    if db_device:
        update_data = device.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_device, key, value)
        db.commit()
        db.refresh(db_device)
    return db_device

def delete_device(db: Session, ip_address: str):
    db_device = get_device_by_ip(db, ip_address)
    if db_device:
        db.delete(db_device)
        db.commit()
    return db_device