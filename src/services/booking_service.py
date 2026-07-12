from fastapi import HTTPException
from sqlalchemy.orm import Session
from db_models import Booking as DBBooking
from models import BookingCreate, BookingUpdate

class BookingService:
    @staticmethod
    def _check_overlap(db: Session, staff_name: str, start_time, end_time, exclude_booking_id: str = None):
        query = db.query(DBBooking).filter(
            DBBooking.staff_name == staff_name,
            DBBooking.status != "cancelled",
            DBBooking.start_time < end_time,
            DBBooking.end_time > start_time
        )
        if exclude_booking_id:
            query = query.filter(DBBooking.booking_id != exclude_booking_id)
            
        overlapping = query.first()
        if overlapping:
            raise HTTPException(status_code=400, detail=f"该技师在此时间段内已有预约排班，无法重复安排。")

    @staticmethod
    def create_booking(db: Session, booking_in: BookingCreate) -> DBBooking:
        BookingService._check_overlap(db, booking_in.staff_name, booking_in.start_time, booking_in.end_time)
        
        db_booking = DBBooking(**booking_in.model_dump())
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return db_booking

    @staticmethod
    def get_all_bookings(db: Session):
        return db.query(DBBooking).all()

    @staticmethod
    def get_client_bookings(db: Session, client_id: str):
        return db.query(DBBooking).filter(DBBooking.client_id == client_id).all()

    @staticmethod
    def update_booking(db: Session, booking_id: str, booking_in: BookingUpdate):
        db_booking = db.query(DBBooking).filter(DBBooking.booking_id == booking_id).first()
        if not db_booking:
            return None
        
        # Check overlap if status is not cancelled
        new_staff = booking_in.staff_name if booking_in.staff_name is not None else db_booking.staff_name
        new_start = booking_in.start_time if booking_in.start_time is not None else db_booking.start_time
        new_end = booking_in.end_time if booking_in.end_time is not None else db_booking.end_time
        new_status = booking_in.status if booking_in.status is not None else db_booking.status

        if new_status != "cancelled":
            BookingService._check_overlap(db, new_staff, new_start, new_end, exclude_booking_id=booking_id)
        
        update_data = booking_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_booking, key, value)
            
        db.commit()
        db.refresh(db_booking)
        return db_booking

    @staticmethod
    def delete_booking(db: Session, booking_id: str):
        db_booking = db.query(DBBooking).filter(DBBooking.booking_id == booking_id).first()
        if db_booking:
            db.delete(db_booking)
            db.commit()
            return True
        return False