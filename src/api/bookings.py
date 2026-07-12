from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from models import Booking, BookingCreate, BookingUpdate
from services.booking_service import BookingService
from database import get_db

router = APIRouter()

@router.post("/", response_model=Booking)
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    return BookingService.create_booking(db, booking)

@router.get("/", response_model=List[Booking])
def list_bookings(db: Session = Depends(get_db)):
    return BookingService.get_all_bookings(db)

@router.get("/client/{client_id}", response_model=List[Booking])
def get_client_bookings(client_id: str, db: Session = Depends(get_db)):
    return BookingService.get_client_bookings(db, client_id)

@router.put("/{booking_id}", response_model=Booking)
def update_booking(booking_id: str, booking_update: BookingUpdate, db: Session = Depends(get_db)):
    booking = BookingService.update_booking(db, booking_id, booking_update)
    if not booking:
        raise HTTPException(status_code=404, detail="未找到该预约记录")
    return booking

@router.delete("/{booking_id}")
def delete_booking(booking_id: str, db: Session = Depends(get_db)):
    success = BookingService.delete_booking(db, booking_id)
    if not success:
        raise HTTPException(status_code=404, detail="未找到该预约记录")
    return {"message": "预约已取消"}