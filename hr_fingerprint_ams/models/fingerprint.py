# -*- coding: utf-8 -*-

import logging
import pytz
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from math import floor
from rule_attendance import *

_logger = logging.getLogger(__name__)

class FingerAttendance(models.Model):
    """
    Saves AMS Solutions data. Each row creates attendance based on condition:
    1. Sign-in/out condition.
    2. Pengecualian condition (action reason).
    """
    _name = 'hr_fingerprint_ams.attendance'
    _description = 'Fingerprint Attendance'
    _rec_name = 'employee_name'

    db_id = fields.Integer('DB ID')
    terminal_id = fields.Integer('Terminal ID')
    nik = fields.Char('NIK')
    employee_name = fields.Char('Employee Name')
    auto_assign = fields.Boolean('Auto-Assign')
    date = fields.Date('Date')
    work_schedules = fields.Char('Work Schedules', help='Used to look up resource calendar.')
    time_start = fields.Float('Working Time Start', help='Time format in hh:mm')
    time_end = fields.Float('Working Time End', help='Time format in hh:mm')
    sign_in = fields.Float('Sign In', help='Time format in hh:mm')
    sign_out = fields.Float('Sign Out', help='Time format in hh:mm')
    day_normal = fields.Integer('Day Normal')
    day_finger = fields.Integer('Day Finger')
    hour_late = fields.Float('Hour Late', help='Time format in hh:mm')
    hour_early_leave = fields.Float('Hour Early Leave', help='Time format in hh:mm')
    absent = fields.Boolean('Absent')
    hour_overtime = fields.Float('Hour Overtime', help='Time format in hh:mm')
    hour_work = fields.Float('Hour Work', help='Time format in hh:mm')
    action_reason = fields.Char('Action Reason', help='Attendance Action Desc')
    required_in = fields.Boolean('Required In')
    required_out = fields.Boolean('Required Out')
    department = fields.Char('Departemen')
    day_weekday = fields.Integer('Weekday')
    day_weekend = fields.Integer('Weekend')
    day_holiday = fields.Integer('Holiday')
    hour_attendance = fields.Float('Hour Attendance', help='Time format in hh:mm')
    hour_ot_normal = fields.Float('Hour OT Normal', help='Time format in hh:mm')
    hour_ot_weekend = fields.Float('Hour OT Weekend', help='Time format in hh:mm')
    hour_ot_holiday = fields.Float('Hour OT Holiday', help='Time format in hh:mm')
    attendance_ids = fields.One2many('hr.attendance', 'finger_attendance_id', 'HR Attendance')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed'),
                              ('approved', 'Approved'),
                              ('correction', 'Correction'),
                              ('payslip', 'Payslip'),
                              ('attendance', 'No Attendance Created')],
                             default='draft',
                             help='Import will update fingerprint attendance with draft state only.')

    # @api.multi
    # @api.constrains('day_normal', 'day_finger')
    # def _check_day_normal_finger(self):
    #     """ Import problem: day normal/finger not imported."""
    #     for record in self:
    #         print 'day_normal %s %s' % (record.day_normal, record.day_finger)
    #         if record.day_normal == 0:
    #             err_msg = _('You have day normal or day finger zero value.\n')
    #             raise ValidationError(err_msg)


    @api.multi
    @api.constrains('sign_in', 'sign_out')
    def _check_sign_in_out(self):
        """ overlap work time creates sign-in and sign-out when employee had fingered multiple times"""
        for record in self:
            # overlap work time creates double sign-in/sign-out
            if (record.sign_in == record.sign_out) and not record.action_reason:
                err_msg = _('%s NIK %s at %s has exact sign-in and sign-out. '
                            'Delete one of them.' % (record.employee_name, record.nik, record.date))
                raise ValidationError(err_msg)

    @api.multi
    @api.constrains('day_normal', 'day_finger')
    def _check_day_normal_finger(self):
        for record in self:
            if record.day_normal == 0:
                err_msg = _('%s NIK %s at %s has 0 day normal/finger. '
                            'Day normal should be 1.' % (record.employee_name, record.nik, record.date))
                raise ValidationError(err_msg)

            if record.day_normal > 1:
                err_msg = _('%s NIK %s at %s has day normal/finger more than 1. '
                            'Maximum value is 1.' % (record.employee_name, record.nik, record.date))
                raise ValidationError(err_msg)

    @api.model
    def create(self, vals):
        """Create and update using same CSV format of fingerprint.
        Must meet attendance rule:
        1. It must be registered employee (name and employee identification number).
        2. It has sign-in/out OR has registered action reason.
        3. OR It has sign-in/out if upkeep attendance code's requirement is single.
        """
        f_attendance_obj = self.env['hr_fingerprint_ams.attendance']

        # override AMS time setup
        vals = self.cleansing(vals)

        # update purposes
        current = f_attendance_obj.search([('db_id', '=', vals['db_id']),
                                           ('terminal_id', '=', vals['terminal_id']),
                                           ('employee_name', '=', vals['employee_name']),
                                           ('nik', '=', vals['nik']),
                                           ('date', '=', vals['date'])])

        # inherited method create should return a recordset
        res = self

        # rule #1 - must be an employee with nik
        attendance = Attendance(self._get_employee(vals['employee_name'], vals['nik']),
                                vals['sign_in'],
                                vals['sign_out'])
        attendance_code_ids = self.env['estate.hr.attendance'].search([('fingerprint', '=', 'single')])

        # rule #2 - must have (sign-in OR sign-out) or (sign-in AND sign-out)
        if len(attendance_code_ids) > 0:
            # rule #3 - OR It has sign-in/out if upkeep attendance code's requirement is single.
            att_rule = AttendanceSpecification().\
                and_specification(EmployeeSpecification()).\
                and_specification(SignInOutSpecification())
        else:
            att_rule = AttendanceSpecification().\
                and_specification(EmployeeSpecification()).\
                and_specification(SignInSpecification()).\
                and_specification(SignOutSpecification())

        if att_rule.is_satisfied_by(attendance):
            if current:
                # update record
                if current.state == 'draft':
                    current.write(vals)
                    res = current
                    self._create_attendance(res, vals, 'sign_in', True)
                    self._create_attendance(res, vals, 'sign_out', True)
            else:
                # create new record
                res = super(FingerAttendance, self).create(vals)
                self._create_attendance(res, vals)
                self._create_attendance(res, vals, 'sign_out')
        else:
            # rule #2 - applied when there is no attendance code with single fingerprint requirements

            # do not create fingerprint attendance if employee not found
            try:
                self._get_employee(vals['employee_name'], vals['nik']).id
            except AttributeError:
                err_msg = _('Fingerprint not created. %s (%s), %s is not registered as employee.' %
                            (vals['employee_name'], vals['nik'], vals['date']))
                _logger.info(err_msg)
                return self

            # create only fingerprint attendance with action reason
            action_reason_ids = self.env['hr.action.reason'].search([('active', '=', True),
                                                                     ('action_type', '=', 'action')])
            item = []
            for action_reason in action_reason_ids:
                item.append(action_reason['name'])
            if vals['action_reason'] in item:
                if current:
                    # Only update fingerprint attendance with draft status
                    if current.state == 'draft':
                        current.attendance_ids.unlink()
                        current.write(vals)
                        res = current
                        self._create_attendance(res, vals, 'action')
                else:
                    res = super(FingerAttendance, self).create(vals)
                    self._create_attendance(res, vals, 'action')

        return res

    @api.model
    def _create_attendance(self, f_attendance, vals, action='sign_in', update=False):
        """
        Finger Attendance make use of HR Attendance.
        :param f_attendance: fingerprint attendance
        :param vals: data
        :param action: sign_in or sign_out
        :param update: set True for update action
        :return: instance of attendance
        """
        employee_id = self._get_employee(vals['employee_name'], vals['nik'])

        att_time = 0
        action_reason_id = self.env['hr.action.reason']

        if action == 'sign_in':
            att_time = vals['sign_in']
        elif action == 'sign_out':
            att_time = vals['sign_out']
        elif action == 'action':
            if vals['sign_in']:
                att_time = vals['sign_in']
            elif vals['sign_out']:
                att_time = vals['sign_out']
            else:
                # action without sign_in/out time
                att_time = 0

            if vals['action_reason']:
                action_reason_id = self.env['hr.action.reason'].search([('active', '=', True),
                                                                        ('name', '=', vals['action_reason'])],
                                                                       limit=1)
        # Overnight schedule
        schedule_id = self.env['hr_time_labour.schedule'].search([('name', '=', f_attendance.work_schedules)], limit=1)
        if schedule_id.overnight_schedule is True and action == 'sign_out':
            date_in = datetime.strptime(vals['date'], '%Y-%m-%d')
            date_out = date_in + relativedelta(days=1)
            vals['date'] = date_out.strftime('%Y-%m-%d')

        att = {
            'finger_attendance_id': f_attendance.id,
            'employee_id': employee_id.id,
            'name': self._get_name(vals['date'], att_time),
            'action': action,
            'action_desc': action_reason_id.id,
        }

        # Cannot overide hr.attendance._worked_hours_compute
        if action == 'action':
            att['worked_hours'] = action_reason_id.action_duration

        if update:
            attendance_obj = self.env['hr.attendance']
            attendance_id = attendance_obj.search([('finger_attendance_id', '=', f_attendance.id),
                                                   ('action', '=', action)])
            res = attendance_id
            res.write(att)
        else:
            res = self.env['hr.attendance'].create(att)

        return res

    @api.multi
    def unlink(self):
        """
        Attendance follow Fingerprint
        :return:
        """
        for f_attendance in self:
            if f_attendance.state != 'draft':
                error_msg = _('You cannot delete approved Fingerprint records.')
                raise ValidationError(error_msg)

        return super(FingerAttendance, self).unlink()

    @api.model
    def _get_employee(self, employee_name, nik):
        """
        Need to check if imported data is an active registered employee or not.
        Args:
            employee_name: name
            employee_id: 10 digits employee registration number
        Returns: instance of an employee or false
        """
        ids = self.env['hr.employee'].search([('name', '=', employee_name),
                                              ('nik_number', '=', nik),
                                              ('active', '=', 1)])
        return ids and ids[0] or False

    @api.model
    def _get_name(self, att_date, att_time):
        """
        Attendance required datetime object
        :param att_date: fingerprint date
        :param att_time: fingerprint time
        :return: instance of datetime UTC
        """
        hour = 0 if att_time == 0 else int(floor(att_time))
        minute = 0 if att_time == 0 else int(round((att_time - hour) * 60))  # widget float_time use round
        second = '00'

        if att_date == '':
            return

        import_dt = datetime.strptime(att_date + ' ' + str(hour) + ':'
                                      + str(minute) + ':' + second, DT)

        # Odoo used UTC (timestamp without timezone).
        # local = pytz.timezone(self._context['tz'])  # user timezone should match import time
        # local_dt = local.localize(import_dt, is_dst=None)
        # res = local_dt.astimezone(pytz.utc)

        return import_dt

    @api.one
    def button_confirmed(self):
        self.write({
            'state': 'confirmed'
        })

    @api.one
    def button_approved(self):
        """Create analytic journal entry
        """
        self.write({
            'state': 'approved'
        })

    @api.multi
    def confirm_all(self):
        """ One by one confirmation takes time."""

        # Server action menu cannot limited by groups_id
        if not self.user_has_groups('base.group_hr_ho_user'):
            err_msg = _('You are not authorized to confirm all fingerprint imported data')
            raise ValidationError(err_msg)

        for record in self:
            if not record.state == 'draft':
                err_msg = _('Selected records is not a draft data.')
                raise ValidationError(err_msg)

        self.write({'state': 'confirmed'})

        # Log confirm all action
        confirm_date = datetime.today()
        current_user = self.env.user
        _logger.info(_('%s confirmed imported AMS fingerprint at %s (server time)' % (current_user.name, confirm_date)))

    @api.multi
    def approve_all_admin(self):
        """ User required single approval level"""

        if not self.user_has_groups('base.group_hr_user'):
            err_msg = _('You are not authorized to approve all fingerprint data')
            raise ValidationError(err_msg)

        for record in self:
            if not record.state in ('draft', 'confirmed'):
                err_msg = _('Selected records is not a draft data.')
                raise ValidationError(err_msg)

        fingerprint_ids = self.search([('id', 'in', self.ids), ('state', 'in', ('draft', 'confirmed'))])
        fingerprint_ids.write({
            'state': 'approved'
        })

        # Log confirm all action
        confirm_date = datetime.today()
        current_user = self.env.user
        _logger.info(_('%s approved fingerprint data at %s (server time)' % (current_user.name, confirm_date)))

    @api.multi
    def approve_all(self):
        """ One by one confirmation takes time."""

        # Server action menu cannot limited by groups_id
        if not self.user_has_groups('base.group_hr_manager'):
            err_msg = _('You are not authorized to approve all fingerprint imported data')
            raise ValidationError(err_msg)

        for record in self:
            if not record.state == 'confirmed':
                err_msg = _('Selected records is not a confirmed data.')
                raise ValidationError(err_msg)

        self.write({'state': 'approved'})

        # Log confirm all action
        confirm_date = datetime.today()
        current_user = self.env.user
        _logger.info(_('%s approved imported AMS fingerprint at %s (server time)' % (current_user.name, confirm_date)))

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        """Remove sum of .
        """

        # No need to sum time_start, time_end, sign_in and sign_out
        if 'time_start' in fields:
            fields.remove('time_start')

        if 'time_end' in fields:
            fields.remove('time_end')

        if 'sign_in' in fields:
            fields.remove('sign_in')

        if 'sign_out' in fields:
            fields.remove('sign_out')

        return super(FingerAttendance, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby, lazy)

    @api.model
    def cleansing(self, vals):
        """
        Some data need to be validated before saved.
        :return: vals
        """
        employee_id = self.env['hr.employee'].search([('name', '=', vals['employee_name']),
                                                      ('nik_number', '=', vals['nik'])])
        contract_id = self.env['hr.contract'].current(employee_id)
        day = datetime.strptime(vals['date'], DF).strftime('%w')

        # Cleansing time start and date
        vals['time_start'], vals['time_end'] = self._fix_day_in_out(contract_id, day)

        return vals

    @api.model
    def _fix_day_in_out(self, contract_id, day):
        """
        Fix time in and time out based on employee calendar.
        :param contract_id: employee contract recordset
        :param day: day of the week, sunday is 0
        :type: integer
        :return: list of float
        """

        if contract_id is None:
            err_msg = _('No contract found.')
            raise ValueError(err_msg)

        if contract_id.working_hours is None:
            err_msg = _('No working hours defined.')
            raise ValueError(err_msg)

        calendar_id = self.env['resource.calendar'].browse(contract_id.working_hours.id)
        time_start, time_end = calendar_id._get_day_in_out(day)

        return time_start, time_end
