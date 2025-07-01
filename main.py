from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List

import crud, schemas, scanner
from database import SessionLocal, Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/devices/", response_model=List[schemas.Device])
def read_devices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    devices = crud.get_devices(db, skip=skip, limit=limit)
    return devices

@app.post("/devices/", response_model=schemas.Device)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    db_device = crud.get_device_by_ip(db, ip_address=device.ip_address)
    if db_device:
        return crud.update_device(db=db, ip_address=device.ip_address, device=device)
    return crud.create_device(db=db, device=device)

@app.get("/scan/{network:path}")
def start_scan(network: str):
    up_hosts, down_hosts = scanner.scan_network(network)
    if up_hosts is None:
        raise HTTPException(status_code=400, detail="Invalid network format")
    return {"message": f"扫描完成，发现 {len(up_hosts)} 个在线设备", "online_hosts": up_hosts, "offline_hosts": down_hosts}