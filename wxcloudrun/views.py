from datetime import datetime
from typing import List

from flask import render_template, request
from sqlalchemy import or_

from wxcloudrun import app, db
from wxcloudrun.dao import session_scope
from wxcloudrun.dify_client import DifyClient, build_alert_payload
from wxcloudrun.model import (
    Alert,
    DeviceConnection,
    MedicationOrder,
    MonitoringParameter,
    MonitoringSession,
    OperatingRoom,
    ParameterReading,
    ParameterThreshold,
    Patient,
)
from wxcloudrun.response import make_err_response, make_succ_response


dify_client = DifyClient()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/rooms', methods=['GET', 'POST'])
def rooms():
    if request.method == 'GET':
        rooms = OperatingRoom.query.order_by(OperatingRoom.name).all()
        return make_succ_response([room.to_dict() for room in rooms])

    payload = request.get_json() or {}
    name = payload.get('name')
    if not name:
        return make_err_response('手术间名称不能为空')

    room = OperatingRoom(
        name=name,
        location=payload.get('location'),
        description=payload.get('description'),
        is_active=payload.get('is_active', True),
    )
    db.session.add(room)
    db.session.commit()
    return make_succ_response(room.to_dict())


@app.route('/api/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id: int):
    room = OperatingRoom.query.get_or_404(room_id)
    return make_succ_response(room.to_dict())


@app.route('/api/rooms/<int:room_id>/devices', methods=['POST'])
def create_device(room_id: int):
    OperatingRoom.query.get_or_404(room_id)
    payload = request.get_json() or {}
    device = DeviceConnection(
        room_id=room_id,
        device_type=payload.get('device_type', 'monitor'),
        name=payload.get('name', '监护设备'),
        manufacturer=payload.get('manufacturer'),
        model=payload.get('model'),
        endpoint=payload.get('endpoint'),
        api_key=payload.get('api_key'),
        enabled=payload.get('enabled', True),
        config=payload.get('config') or {},
    )
    db.session.add(device)
    db.session.commit()
    return make_succ_response(device.to_dict(include_parameters=True))


@app.route('/api/devices/<int:device_id>', methods=['GET'])
def get_device(device_id: int):
    device = DeviceConnection.query.get_or_404(device_id)
    return make_succ_response(device.to_dict(include_parameters=True))


@app.route('/api/devices/<int:device_id>/parameters', methods=['POST'])
def create_parameter(device_id: int):
    DeviceConnection.query.get_or_404(device_id)
    payload = request.get_json() or {}
    key = payload.get('key')
    display_name = payload.get('display_name')
    if not key or not display_name:
        return make_err_response('参数标识和名称不能为空')

    parameter = MonitoringParameter(
        device_connection_id=device_id,
        key=key,
        display_name=display_name,
        unit=payload.get('unit'),
        data_type=payload.get('data_type', 'float'),
    )
    db.session.add(parameter)
    db.session.commit()
    return make_succ_response(parameter.to_dict(include_threshold=True))


@app.route('/api/parameters/<int:parameter_id>/threshold', methods=['POST'])
def configure_threshold(parameter_id: int):
    MonitoringParameter.query.get_or_404(parameter_id)
    payload = request.get_json() or {}
    threshold = ParameterThreshold.query.filter_by(parameter_id=parameter_id).first()
    if threshold is None:
        threshold = ParameterThreshold(parameter_id=parameter_id)
        db.session.add(threshold)

    threshold.min_value = payload.get('min_value')
    threshold.max_value = payload.get('max_value')
    threshold.severity = payload.get('severity', threshold.severity)
    threshold.notes = payload.get('notes')
    db.session.commit()
    return make_succ_response(threshold.to_dict())


@app.route('/api/patients', methods=['GET'])
def list_patients():
    keyword = request.args.get('keyword')
    query = Patient.query
    if keyword:
        like_keyword = f"%{keyword}%"
        query = query.filter(
            or_(Patient.name.ilike(like_keyword), Patient.medical_record_number.ilike(like_keyword))
        )
    patients = query.order_by(Patient.name).limit(50).all()
    return make_succ_response([patient.to_dict(include_medications=True) for patient in patients])


@app.route('/api/sessions', methods=['GET', 'POST'])
def sessions():
    if request.method == 'GET':
        active_sessions = MonitoringSession.query.filter_by(status='active').order_by(MonitoringSession.started_at.desc()).all()
        return make_succ_response([session.to_dict() for session in active_sessions])

    payload = request.get_json() or {}
    room_id = payload.get('room_id')
    patient_data = payload.get('patient')
    if not room_id or not patient_data:
        return make_err_response('缺少手术间或患者信息')

    room = OperatingRoom.query.get(room_id)
    if room is None:
        return make_err_response('手术间不存在')

    mrn = patient_data.get('medical_record_number')
    if not mrn:
        return make_err_response('患者病历号不能为空')

    patient = Patient.query.filter_by(medical_record_number=mrn).first()
    if patient is None:
        patient = Patient(
            medical_record_number=mrn,
            name=patient_data.get('name', '未知患者'),
            sex=patient_data.get('sex'),
            age=patient_data.get('age'),
            allergies=patient_data.get('allergies'),
            diagnosis=patient_data.get('diagnosis'),
            notes=patient_data.get('notes'),
        )
        db.session.add(patient)
        db.session.flush()
    else:
        patient.name = patient_data.get('name', patient.name)
        patient.sex = patient_data.get('sex', patient.sex)
        patient.age = patient_data.get('age', patient.age)
        patient.allergies = patient_data.get('allergies', patient.allergies)
        patient.diagnosis = patient_data.get('diagnosis', patient.diagnosis)
        patient.notes = patient_data.get('notes', patient.notes)

    medications = payload.get('medications') or []
    if medications:
        MedicationOrder.query.filter_by(patient_id=patient.id).delete(synchronize_session=False)
        for med in medications:
            order = MedicationOrder(
                patient_id=patient.id,
                name=med.get('name', '未命名用药'),
                route=med.get('route'),
                dosage=med.get('dosage'),
                schedule=med.get('schedule'),
            )
            db.session.add(order)

    session = MonitoringSession(patient_id=patient.id, room_id=room.id, status='active')
    db.session.add(session)
    db.session.commit()
    return make_succ_response(session.to_dict())


@app.route('/api/sessions/<int:session_id>', methods=['GET'])
def get_session(session_id: int):
    session = MonitoringSession.query.get_or_404(session_id)
    return make_succ_response(session.to_dict())


def _evaluate_alerts(session: MonitoringSession, readings: List[ParameterReading]):
    alerts_triggered = []
    for reading in readings:
        parameter = reading.parameter
        threshold = parameter.threshold if parameter else None
        if threshold is None:
            continue

        message = None
        unit = f" {parameter.unit}" if parameter and parameter.unit else ''
        if threshold.min_value is not None and reading.value < threshold.min_value:
            message = f"{parameter.display_name} 当前值 {reading.value}{unit} 低于设定下限 {threshold.min_value}{unit}"
        if threshold.max_value is not None and reading.value > threshold.max_value:
            message = f"{parameter.display_name} 当前值 {reading.value}{unit} 超过设定上限 {threshold.max_value}{unit}"

        if message:
            alert = Alert(
                session_id=session.id,
                parameter_id=reading.parameter_id,
                value=reading.value,
                message=message,
                severity=threshold.severity or 'warning',
                triggered_at=datetime.utcnow(),
            )
            db.session.add(alert)
            alerts_triggered.append(alert)
    return alerts_triggered


def _notify_dify(session: MonitoringSession, alerts: List[Alert]):
    if not alerts:
        return

    for alert in alerts:
        parameter = alert.parameter
        patient = session.patient
        room = session.room
        context = {
            'operating_room': room.name if room else None,
            'patient_name': patient.name if patient else None,
            'medical_record_number': patient.medical_record_number if patient else None,
            'diagnosis': patient.diagnosis if patient else None,
            'active_medications': [med.name for med in patient.medications],
            'parameter': parameter.display_name if parameter else None,
            'value': alert.value,
            'unit': parameter.unit if parameter else None,
            'threshold_min': parameter.threshold.min_value if parameter and parameter.threshold else None,
            'threshold_max': parameter.threshold.max_value if parameter and parameter.threshold else None,
            'alert_message': alert.message,
            'severity': alert.severity,
        }
        payload = build_alert_payload(context)
        recommendation = dify_client.send_alert(payload)
        if recommendation:
            alert.dify_recommendation = recommendation
    db.session.commit()


@app.route('/api/sessions/<int:session_id>/ingest', methods=['POST'])
def ingest_readings(session_id: int):
    session = MonitoringSession.query.get_or_404(session_id)
    if session.status != 'active':
        return make_err_response('监测会话已结束')

    payload = request.get_json() or {}
    parameters = payload.get('parameters') or []
    if not parameters:
        return make_err_response('缺少监测参数数据')

    readings: List[ParameterReading] = []
    with session_scope() as txn:
        for item in parameters:
            parameter_id = item.get('parameter_id')
            value = item.get('value')
            if parameter_id is None or value is None:
                continue
            parameter = MonitoringParameter.query.get(parameter_id)
            if parameter is None:
                continue
            reading = ParameterReading(
                session_id=session.id,
                parameter_id=parameter.id,
                value=float(value),
                recorded_at=datetime.utcnow(),
            )
            txn.add(reading)
            txn.flush()
            readings.append(reading)
    alerts = _evaluate_alerts(session, readings)
    db.session.commit()
    _notify_dify(session, alerts)
    response = {
        'readings': [reading.to_dict() for reading in readings],
        'alerts': [alert.to_dict() for alert in alerts],
    }
    return make_succ_response(response)


@app.route('/api/sessions/<int:session_id>/alerts', methods=['GET'])
def list_alerts(session_id: int):
    MonitoringSession.query.get_or_404(session_id)
    alerts = Alert.query.filter_by(session_id=session_id).order_by(Alert.triggered_at.desc()).all()
    return make_succ_response([alert.to_dict() for alert in alerts])


@app.route('/api/sessions/<int:session_id>/resolve/<int:alert_id>', methods=['POST'])
def resolve_alert(session_id: int, alert_id: int):
    alert = Alert.query.filter_by(session_id=session_id, id=alert_id).first_or_404()
    alert.resolved = True
    alert.updated_at = datetime.utcnow()
    db.session.commit()
    return make_succ_response(alert.to_dict())
