# -*- coding: utf-8 -*-
{
    'name': "Estate Workshop",

    'summary': """
        Modul Workshop for Estate""",

    'description': """
        This module to maintenance every asset in companies,
    """,

    'author': "Mahroza And Probo",
    'website': "http://www.palmagroup.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','asset','mro','estate_vehicle'],

    #to create sql in odoo
    # 'update_xml': ["query.sql","query_hke.sql","job_scheduling.sql"],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/estate_asset.xml',
        'views/inherit_mro_request.xml',
        'views/estate_master_catalog.xml',
        'views/estate_mecanic_timesheet.xml',
        'views/estate_master_workshop_schedule.xml',
        'views/estate_master_mapping_asset.xml',
        'views/equipment_maintenance_order.xml',
        'views/estate_service_external.xml',
        'views/estate_workshop_cost.xml',
        'views/inherit_mro_order.xml',
        'views/task_maintenance_order.xml',
        'views/inherit_hr_contract.xml',
        'views/view_cost_workshop.xml',
        'views/estate_workshop_sparepart.xml',
        'views/estate_workshop_procurement.xml',
        'views/view_master_effectivedate_calendar.xml',
        'views/view_summary_vehicle_status.xml',
        'views/inherit_fleet_vehicle.xml',
        'views/Inherit_view_summary_cost_vehicle.xml',
        'views/view_wwa_vehicle.xml',
        'data/scheduler_workshop.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
        'demo/estate.activity.csv',
        'demo/estate_job_employee.xml',
        'demo/estate_workshop_code.xml',
        'demo/fleet.vehicle.csv',
        'demo/product.uom.csv',
        # 'demo/product.ul.csv',
        'demo/product.category.csv',
        'demo/product.template.csv',
        # 'demo/product.packaging.csv',
        'demo/asset.asset.csv'


    ],
}