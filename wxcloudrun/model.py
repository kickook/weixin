from datetime import datetime
from typing import Optional

from werkzeug.security import generate_password_hash

from wxcloudrun import db
import config


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)


class User(db.Model, TimestampMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False, default='clinician')
    hashed_password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class OperatingRoom(db.Model, TimestampMixin):
    __tablename__ = 'operating_rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    location = db.Column(db.String(255))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self, include_devices: bool = True):
        data = {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'description': self.description,
            'is_active': self.is_active,
        }
        if include_devices:
            data['devices'] = [device.to_dict(include_parameters=True) for device in self.devices]
        return data


class DeviceConnection(db.Model, TimestampMixin):
    __tablename__ = 'device_connections'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('operating_rooms.id'), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    manufacturer = db.Column(db.String(120))
    model = db.Column(db.String(120))
    endpoint = db.Column(db.String(255))
    api_key = db.Column(db.String(255))
    enabled = db.Column(db.Boolean, default=True)
    config = db.Column(db.JSON, default={})

    room = db.relationship('OperatingRoom', backref=db.backref('devices', lazy='joined'))

    def to_dict(self, include_parameters: bool = False):
        data = {
            'id': self.id,
            'room_id': self.room_id,
            'device_type': self.device_type,
            'name': self.name,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'endpoint': self.endpoint,
            'enabled': self.enabled,
            'config': self.config or {},
        }
        if include_parameters:
            data['parameters'] = [parameter.to_dict(include_threshold=True) for parameter in self.parameters]
        return data


class Patient(db.Model, TimestampMixin):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    medical_record_number = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    sex = db.Column(db.String(10))
    age = db.Column(db.Integer)
    allergies = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    notes = db.Column(db.Text)

    def to_dict(self, include_medications: bool = False):
        data = {
            'id': self.id,
            'medical_record_number': self.medical_record_number,
            'name': self.name,
            'sex': self.sex,
            'age': self.age,
            'allergies': self.allergies,
            'diagnosis': self.diagnosis,
            'notes': self.notes,
        }
        if include_medications:
            data['medications'] = [med.to_dict() for med in self.medications]
        return data


class MedicationOrder(db.Model, TimestampMixin):
    __tablename__ = 'medication_orders'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    route = db.Column(db.String(50))
    dosage = db.Column(db.String(50))
    schedule = db.Column(db.String(120))
    start_time = db.Column(db.DateTime)
    stop_time = db.Column(db.DateTime)

    patient = db.relationship('Patient', backref=db.backref('medications', lazy='joined'))

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'name': self.name,
            'route': self.route,
            'dosage': self.dosage,
            'schedule': self.schedule,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'stop_time': self.stop_time.isoformat() if self.stop_time else None,
        }


class MonitoringParameter(db.Model, TimestampMixin):
    __tablename__ = 'monitoring_parameters'

    id = db.Column(db.Integer, primary_key=True)
    device_connection_id = db.Column(db.Integer, db.ForeignKey('device_connections.id'), nullable=False)
    key = db.Column(db.String(120), nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    unit = db.Column(db.String(30))
    data_type = db.Column(db.String(30), default='float')

    device = db.relationship('DeviceConnection', backref=db.backref('parameters', lazy='joined'))

    __table_args__ = (db.UniqueConstraint('device_connection_id', 'key', name='uq_param_device_key'),)

    def to_dict(self, include_threshold: bool = False):
        data = {
            'id': self.id,
            'device_connection_id': self.device_connection_id,
            'key': self.key,
            'display_name': self.display_name,
            'unit': self.unit,
            'data_type': self.data_type,
        }
        if include_threshold:
            data['threshold'] = self.threshold.to_dict() if self.threshold else None
        return data


class ParameterThreshold(db.Model, TimestampMixin):
    __tablename__ = 'parameter_thresholds'

    id = db.Column(db.Integer, primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey('monitoring_parameters.id'), nullable=False, unique=True)
    min_value = db.Column(db.Float)
    max_value = db.Column(db.Float)
    severity = db.Column(db.String(30), default='warning')
    notes = db.Column(db.Text)

    parameter = db.relationship('MonitoringParameter', backref=db.backref('threshold', uselist=False))

    def to_dict(self):
        return {
            'id': self.id,
            'parameter_id': self.parameter_id,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'severity': self.severity,
            'notes': self.notes,
        }


class MonitoringSession(db.Model, TimestampMixin):
    __tablename__ = 'monitoring_sessions'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('operating_rooms.id'), nullable=False)
    status = db.Column(db.String(30), default='active')
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)

    patient = db.relationship('Patient', backref=db.backref('sessions', lazy='dynamic'))
    room = db.relationship('OperatingRoom', backref=db.backref('sessions', lazy='dynamic'))

    def to_dict(self, include_patient: bool = True, include_room: bool = True):
        data = {
            'id': self.id,
            'patient_id': self.patient_id,
            'room_id': self.room_id,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
        }
        if include_patient:
            data['patient'] = self.patient.to_dict(include_medications=True) if self.patient else None
        if include_room:
            data['room'] = self.room.to_dict(include_devices=True) if self.room else None
        return data


class ParameterReading(db.Model, TimestampMixin):
    __tablename__ = 'parameter_readings'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('monitoring_sessions.id'), nullable=False)
    parameter_id = db.Column(db.Integer, db.ForeignKey('monitoring_parameters.id'), nullable=False)
    value = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

    session = db.relationship('MonitoringSession', backref=db.backref('readings', lazy='dynamic'))
    parameter = db.relationship('MonitoringParameter', backref=db.backref('readings', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'parameter_id': self.parameter_id,
            'value': self.value,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'parameter': self.parameter.to_dict(include_threshold=True) if self.parameter else None,
        }


class Alert(db.Model, TimestampMixin):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('monitoring_sessions.id'), nullable=False)
    parameter_id = db.Column(db.Integer, db.ForeignKey('monitoring_parameters.id'), nullable=False)
    value = db.Column(db.Float)
    message = db.Column(db.Text)
    severity = db.Column(db.String(30))
    triggered_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    dify_recommendation = db.Column(db.Text)

    session = db.relationship('MonitoringSession', backref=db.backref('alerts', lazy='dynamic'))
    parameter = db.relationship('MonitoringParameter')

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'parameter_id': self.parameter_id,
            'value': self.value,
            'message': self.message,
            'severity': self.severity,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'resolved': self.resolved,
            'dify_recommendation': self.dify_recommendation,
            'parameter': self.parameter.to_dict(include_threshold=True) if self.parameter else None,
        }


def ensure_default_admin():
    username = config.DEFAULT_ADMIN_USERNAME
    existing: Optional[User] = User.query.filter_by(username=username).first()
    if existing:
        return existing

    password = config.DEFAULT_ADMIN_PASSWORD
    user = User(username=username, role=config.DEFAULT_ADMIN_ROLE, hashed_password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return user
