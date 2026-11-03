from django.urls import path
from . import views

urlpatterns = [
    # ورود / خروج
    path('', views.dashboard_redirect, name='dashboard_redirect'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/specifications/lookup/', views.api_specifications_lookup, name='api_spec_lookup'),
    path('api/specifications/list/', views.api_specifications_list, name='api_spec_list'),
    # متقاضی
    path('requester/', views.requester_dashboard, name='requester_dashboard'),
    path('requester/new/', views.new_request_view, name='new_request'),
    path('requester/preview/<int:req_id>/', views.preview_request_view, name='preview_request'),

    # پذیرش
    path('reception/', views.reception_dashboard, name='reception_dashboard'),
    path('reception/action/<int:req_id>/', views.reception_action_view, name='reception_action'),
    path('reception/assign/<int:req_id>/', views.assign_tasks_view, name='assign_tasks'),
    path('reception/export-excel/', views.export_excel_view, name='export_excel'),

    # تایید نهایی (رئیس آزمایشگاه)
    path('reception/final-review/', views.final_review_dashboard, name='final_review_dashboard'),
    path('reception/final-review/<int:req_id>/', views.final_review_action, name='final_review_action'),

    # کارشناس آزمایشگاه
    path('operator/', views.operator_dashboard, name='operator_dashboard'),
    path('operator/accept/<int:req_id>/', views.accept_assignment_view, name='accept_assignment'),
    path('operator/test-entry/<int:req_id>/', views.test_entry_view, name='test_entry'),

    # سرپرست آزمایشگاه
    path('supervisor/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('supervisor/review/<int:assignment_id>/', views.supervisor_review, name='supervisor_review'),

    # اعلان‌ها
    path('request/<int:req_id>/detail/', views.request_detail_view, name='request_detail'),
    path('request/<int:req_id>/report/', views.request_report_view, name='request_report'),
    path('request/<int:req_id>/attachment/', views.request_attachment_view, name='request_attachment'),
    # پیام‌رسانی
    # بکاپ دیتابیس
    path('backup/', views.backup_dashboard, name='backup_dashboard'),
    path('backup/create/', views.backup_create, name='backup_create'),
    path('backup/download-current/', views.backup_download_current, name='backup_download_current'),
    path('backup/download/<str:filename>/', views.backup_download, name='backup_download'),
    path('backup/delete/<str:filename>/', views.backup_delete, name='backup_delete'),
    # گزارش‌ها
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/excel/', views.reports_excel, name='reports_excel'),
    path('reports/print/', views.reports_print, name='reports_print'),
    path('stats/', views.stats_dashboard, name='stats_dashboard'),
    path('messages/', views.messages_inbox, name='messages_inbox'),
    path('messages/compose/', views.message_compose, name='messages_compose'),
    path('messages/view/<int:msg_id>/', views.message_view, name='message_view'),
    path('messages/delete/<int:msg_id>/', views.message_delete, name='message_delete'),
    path('messages/mark-all-read/', views.message_mark_all_read, name='message_mark_all_read'),
    path('messages/unread/<int:msg_id>/', views.message_mark_unread, name='message_mark_unread'),
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/read/<int:notif_id>/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/read-all/', views.notification_mark_all_read, name='notification_mark_all_read'),

    # مدیریت کاربران
    path('users/', views.users_list, name='users_list'),
    path('users/new/', views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    path('users/<int:user_id>/change-password/', views.user_change_password, name='user_change_password'),

    # تجهیزات
    path('equipment/', views.equipment_list, name='equipment_list'),
    path('equipment/new/', views.equipment_create, name='equipment_create'),
    path('equipment/<int:equipment_id>/edit/', views.equipment_edit, name='equipment_edit'),
    path('equipment/<int:equipment_id>/delete/', views.equipment_delete, name='equipment_delete'),

    # استانداردها
    path('standards/', views.standards_list, name='standards_list'),
    path('standards/new/', views.standard_create, name='standard_create'),
    path('standards/<int:standard_id>/edit/', views.standard_edit, name='standard_edit'),
    path('standards/<int:standard_id>/delete/', views.standard_delete, name='standard_delete'),
    # تصاویر نمونه‌ها
    path('samples/images/upload/<int:req_id>/', views.sample_image_upload, name='sample_image_upload'),
    path('samples/images/delete/<int:image_id>/', views.sample_image_delete, name='sample_image_delete'),
    path('samples/images/view/<int:image_id>/', views.sample_image_view, name='sample_image_view'),
    path('samples/images/gallery/<int:req_id>/', views.sample_image_gallery, name='sample_image_gallery'),
    # پروفایل کاربری
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/password/', views.profile_change_password, name='profile_change_password'),
    # QR Code و برچسب نمونه
    path('request/<int:req_id>/qr.png', views.request_qr_image, name='request_qr_image'),
    path('request/<int:req_id>/label/', views.request_qr_label, name='request_qr_label'),
    path('labels/batch/', views.request_qr_batch, name='request_qr_batch'),
    # حدود مجاز استاندارد
    path('specs/', views.spec_list, name='spec_list'),
    path('specs/new/', views.spec_create, name='spec_create'),
    path('specs/<int:spec_id>/edit/', views.spec_edit, name='spec_edit'),
    path('specs/<int:spec_id>/delete/', views.spec_delete, name='spec_delete'),
    path('specs/<int:spec_id>/toggle/', views.spec_toggle, name='spec_toggle'),
    path('specs/import/', views.spec_import_excel, name='spec_import_excel'),
    path('specs/template/', views.spec_template_excel, name='spec_template_excel'),
    path('api/spec/check/', views.spec_api_check, name='spec_api_check'),
    # ورود Excel (لایه‌ی RAW)
    path('excel-import/', views.excel_import_dashboard, name='excel_import_dashboard'),
    path('excel-import/upload/', views.excel_import_upload, name='excel_import_upload'),
    path('excel-import/batch/<int:batch_id>/', views.excel_import_batch_detail, name='excel_import_batch_detail'),
    path('excel-import/search/', views.excel_raw_search, name='excel_raw_search'),
    path('excel-import/row/<int:row_id>/', views.excel_raw_detail, name='excel_raw_detail'),
    # لینک کردن Excel
    path('excel-import/linking/', views.excel_linking_dashboard, name='excel_linking_dashboard'),
    path('excel-import/linking/auto/', views.excel_auto_link_all, name='excel_auto_link_all'),
    path('excel-import/linking/manual/<int:row_id>/', views.excel_manual_link, name='excel_manual_link'),
    path('excel-import/linking/unlink/<int:row_id>/', views.excel_row_unlink, name='excel_row_unlink'),
    path('request/<int:req_id>/with-excel/', views.request_with_excel_detail, name='request_with_excel'),
    # API Excel
    path('api/excel/search/', views.api_excel_search, name='api_excel_search'),
    path('api/excel/row/<int:row_id>/', views.api_excel_row_data, name='api_excel_row_data'),
    # ISO/IEC 17025 — 7.9 Complaints (شکایات)
    path('complaints/', views.complaints_list, name='complaints_list'),
    path('complaints/new/', views.complaint_create, name='complaint_create'),
    path('complaints/<int:complaint_id>/', views.complaint_detail, name='complaint_detail'),
    # ISO/IEC 17025 — 7.10 Non-conforming Work (NC)
    path('nc/', views.nc_list, name='nc_list'),
    path('nc/new/', views.nc_create, name='nc_create'),
    path('nc/<int:nc_id>/', views.nc_detail, name='nc_detail'),
    # ISO/IEC 17025 — 8.8 Internal Audits (ممیزی داخلی)
    path('audits/', views.audit_list, name='audit_list'),
    path('audits/new/', views.audit_create, name='audit_create'),
    path('audits/<int:audit_id>/', views.audit_detail, name='audit_detail'),
    path('audits/<int:audit_id>/print/', views.audit_print, name='audit_print'),
    path('audits/<int:audit_id>/findings/new/', views.audit_finding_create, name='audit_finding_create'),
    path('audits/<int:audit_id>/findings/bulk/', views.audit_findings_bulk_create, name='audit_findings_bulk_create'),
    path('audits/findings/<int:finding_id>/', views.audit_finding_detail, name='audit_finding_detail'),
    # ISO/IEC 17025 — 8.9 Management Review (بازنگری مدیریت)
    path('reviews/', views.mr_list, name='mr_list'),
    path('reviews/new/', views.mr_create, name='mr_create'),
    path('reviews/<int:review_id>/', views.mr_detail, name='mr_detail'),
    path('reviews/<int:review_id>/print/', views.mr_print, name='mr_print'),
    path('reviews/<int:review_id>/actions/new/', views.mr_action_create, name='mr_action_create'),
    path('reviews/actions/<int:action_id>/', views.mr_action_detail, name='mr_action_detail'),
    # ISO/IEC 17025 — 8.5 Risk & Opportunities
    path('risks/', views.risk_list, name='risk_list'),
    path('risks/new/', views.risk_create, name='risk_create'),
    path('risks/<int:risk_id>/', views.risk_detail, name='risk_detail'),

    path('opportunities/', views.opp_list, name='opp_list'),
    path('opportunities/new/', views.opp_create, name='opp_create'),
    path('opportunities/<int:opp_id>/', views.opp_detail, name='opp_detail'),
    # ISO/IEC 17025 — 8.4 Document Control
    path('documents/', views.doc_list, name='doc_list'),
    path('documents/new/', views.doc_create, name='doc_create'),
    path('documents/<int:doc_id>/', views.doc_detail, name='doc_detail'),
    path('documents/<int:doc_id>/print/', views.doc_print, name='doc_print'),
    # ISO/IEC 17025 — 8.3 Records Control
    path('records/', views.records_dashboard, name='records_dashboard'),
    path('records/policies/', views.retention_policy_list, name='retention_policy_list'),
    path('records/policies/new/', views.retention_policy_create, name='retention_policy_create'),
    path('records/policies/<int:policy_id>/', views.retention_policy_detail, name='retention_policy_detail'),
    # ISO/IEC 17025 — 7.2 Method Validation
    path('validations/', views.mv_list, name='mv_list'),
    path('validations/new/', views.mv_create, name='mv_create'),
    path('validations/<int:mv_id>/', views.mv_detail, name='mv_detail'),
    path('validations/<int:mv_id>/print/', views.mv_print, name='mv_print'),
    path('validations/<int:mv_id>/parameters/new/', views.mv_param_create, name='mv_param_create'),
    # ISO/IEC 17025 — 6.5 Traceability / Reference Standards
    path('references/', views.ref_list, name='ref_list'),
    path('references/new/', views.ref_create, name='ref_create'),
    path('references/<int:ref_id>/', views.ref_detail, name='ref_detail'),
    path('references/<int:ref_id>/print/', views.ref_print, name='ref_print'),
    path('references/<int:ref_id>/usages/new/', views.ref_usage_create, name='ref_usage_create'),
    path('reports/mechanical/<int:req_id>/', views.mechanical_report_view, name='mechanical_report'),
    path('mechanical/sync/', views.mechanical_sync_view, name='mechanical_sync'),
    path('mechanical/search/', views.mechanical_search_view, name='mechanical_search'),
    path('mechanical/prepare-print/<int:req_id>/', views.mechanical_prepare_print_view, name='mechanical_prepare_print'),
    path('api/db-lookup/', views.api_db_lookup, name='api_db_lookup'),
    path('api/db-lookup/<int:req_id>/', views.api_db_lookup_detail, name='api_db_lookup_detail'),

    # ─── کالیبراسیون ───
    path('calibration/', views.calibration_registry_list, name='calibration_registry_list'),
    path('calibration/<int:reg_id>/', views.calibration_registry_detail, name='calibration_registry_detail'),


    # ─── تجهیزات مرجع ───
    path('references-admin/', views.ref_equipment_list, name='ref_equipment_list'),
    path('references-admin/new/', views.ref_equipment_create, name='ref_equipment_create'),
    path('references-admin/<int:eq_id>/', views.ref_equipment_detail, name='ref_equipment_detail'),
    path('references-admin/<int:eq_id>/edit/', views.ref_equipment_edit, name='ref_equipment_edit'),
    path('references-admin/<int:eq_id>/delete/', views.ref_equipment_delete, name='ref_equipment_delete'),
    path('references-admin/<int:eq_id>/certificate/', views.ref_certificate_upload, name='ref_certificate_upload'),
    path('references-admin/certificate/<int:cert_id>/set-current/', views.ref_certificate_set_current, name='ref_certificate_set_current'),
    path('references-admin/certificate/<int:cert_id>/delete/', views.ref_certificate_delete, name='ref_certificate_delete'),


    # ─── مستر لیست کالیبراسیون ───
    path('calibration/master-list/', views.calibration_master_list, name='calibration_master_list'),
    path('calibration/equipment/<str:code>/', views.calibration_equipment_history, name='calibration_equipment_history'),


    path('calibration/master-list/print/', views.calibration_master_print, name='calibration_master_print'),


    path('calibration/coding/add/', views.calibration_equipment_add, name='calibration_equipment_add'),
    path('calibration/coding/api/serial/', views.calibration_equipment_add_api, name='calibration_equipment_add_api'),
    path('calibration/coding/guide/', views.calibration_coding_guide, name='calibration_coding_guide'),


    path('calibration/coding/<str:model_type>/create/', views.coding_ref_create, name='coding_ref_create'),
    path('calibration/coding/<str:model_type>/<int:obj_id>/update/', views.coding_ref_update, name='coding_ref_update'),
    path('calibration/coding/<str:model_type>/<int:obj_id>/delete/', views.coding_ref_delete, name='coding_ref_delete'),


    path('calibration/recall/', views.calibration_recall, name='calibration_recall'),
    path('calibration/recall/excel/', views.calibration_recall_excel, name='calibration_recall_excel'),


    path('calibration/recall/print/', views.calibration_recall_print, name='calibration_recall_print'),

    path('calibration/execution-report/', views.calibration_execution_report, name='calibration_execution_report'),
    path('calibration/execution-report/excel/', views.calibration_execution_excel, name='calibration_execution_excel'),
    path('calibration/execution-report/print/', views.calibration_execution_print, name='calibration_execution_print'),



    path('calibration/register/new/', views.calibration_register_new, name='calibration_register_new'),
    path('calibration/api/equipment-lookup/', views.calibration_equipment_lookup_api, name='calibration_equipment_lookup_api'),


    path('calibration/mpe-rules/', views.mpe_rule_list, name='mpe_rule_list'),
    path('calibration/mpe-rules/new/', views.mpe_rule_create, name='mpe_rule_create'),
    path('calibration/mpe-rules/<int:rule_id>/edit/', views.mpe_rule_edit, name='mpe_rule_edit'),
    path('calibration/mpe-rules/<int:rule_id>/delete/', views.mpe_rule_delete, name='mpe_rule_delete'),
    path('calibration/mpe-rules/api/', views.mpe_rule_api_list, name='mpe_rule_api_list'),


    path('calibration/reports/financial/', views.calibration_financial_report, name='calibration_financial_report'),
    path('calibration/reports/financial/excel/', views.calibration_financial_excel, name='calibration_financial_excel'),


    path('calibration/sync-groups/', views.calibration_sync_groups, name='calibration_sync_groups'),

    path('calibration/categories/', views.category_list, name='category_list'),
    path('calibration/categories/create/', views.category_create, name='category_create'),
    path('calibration/categories/<int:cat_id>/edit/', views.category_edit, name='category_edit'),
    path('calibration/categories/<int:cat_id>/delete/', views.category_delete, name='category_delete'),
    path('calibration/reports/financial-v2/', views.calibration_financial_report_v2, name='calibration_financial_report_v2'),


    path('calibration/import/', views.calibration_import_dashboard, name='calibration_import_dashboard'),
    path('calibration/import/run/<str:source>/', views.calibration_import_run, name='calibration_import_run'),


    path('calibration/interval/', views.calibration_interval_list, name='calibration_interval_list'),
    path('calibration/interval/new/', views.calibration_interval_form, name='calibration_interval_new'),
    path('calibration/interval/<int:pk>/', views.calibration_interval_detail, name='calibration_interval_detail'),
    path('calibration/interval/<int:pk>/edit/', views.calibration_interval_form, name='calibration_interval_edit'),
    path('calibration/interval/<int:pk>/delete/', views.calibration_interval_delete, name='calibration_interval_delete'),
    path('calibration/interval/save/', views.calibration_interval_save, name='calibration_interval_save'),


    path('calibration/interval/<int:pk>/print/', views.calibration_interval_print, name='calibration_interval_print'),
    path('calibration/api/ref-equipment-list/', views.api_ref_equipment_list, name='api_ref_equipment_list'),
    path('calibration/outsourced/', views.outsourced_list, name='outsourced_list'),
    path('calibration/outsourced/new/', views.outsourced_create, name='outsourced_create'),
    path('calibration/outsourced/<int:pk>/', views.outsourced_detail, name='outsourced_detail'),
    path('calibration/outsourced/<int:pk>/edit/', views.outsourced_edit, name='outsourced_edit'),
    path('calibration/outsourced/<int:pk>/delete/', views.outsourced_delete, name='outsourced_delete'),
    path('calibration/outsourced/cert-file/<int:pk>/delete/', views.outsourced_cert_file_delete, name='outsourced_cert_file_delete'),
    path('calibration/api/reference-equipment-list/', views.api_reference_equipment_list, name='api_reference_equipment_list'),
    path('calibration/<int:pk>/certificate/', views.calibration_certificate, name='calibration_certificate'),
    path('calibration/<int:pk>/certificate-print/', views.calibration_certificate_print, name='calibration_certificate_print'),
    path('calibration/certificate-builder/', views.certificate_builder, name='certificate_builder'),
    path('calibration/certificate-builder/list/', views.certificate_builder_list, name='certificate_builder_list'),
    path('calibration/certificate-builder/new/', views.certificate_builder_edit, name='certificate_builder_new'),
    path('calibration/certificate-builder/<int:pk>/edit/', views.certificate_builder_edit, name='certificate_builder_edit'),
    path('calibration/certificate-builder/<int:pk>/delete/', views.certificate_builder_delete, name='certificate_builder_delete'),
    path('calibration/certificate-builder/<int:pk>/preview/', views.certificate_builder_preview, name='certificate_builder_preview'),
    path('public/certificate/<int:pk>/', views.public_certificate_view, name='public_certificate_view'),
    path('public/outsourced/<int:pk>/', views.public_outsourced_view, name='public_outsourced_view'),
    path('calibration/cert-file/<int:pk>/archive/', views.archive_cert_file, name='archive_cert_file'),
    path('calibration/cert-file/<int:pk>/unarchive/', views.unarchive_cert_file, name='unarchive_cert_file'),
    path('calibration/outsourced/<int:pk>/archive-all/', views.archive_all_cert_files, name='archive_all_cert_files'),
    path('public/outsourced/<int:pk>/gallery/', views.public_outsourced_gallery, name='public_outsourced_gallery'),
    path('calibration/cert-file/<int:pk>/view/', views.serve_cert_file, name='serve_cert_file'),
    path('public/cert-file/<int:pk>/view/', views.serve_cert_file_public, name='serve_cert_file_public'),
    path('calibration/sync-master/', views.calibration_sync_master, name='calibration_sync_master'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/export/', views.analytics_export_excel, name='analytics_export_excel'),
    path('api/units-by-group/', views.api_units_by_group, name='api_units_by_group'),
    path('calibration/monthly-due/', views.calibration_monthly_due, name='calibration_monthly_due'),
    path('calibration/monthly-due/notify/', views.calibration_monthly_due_notify, name='calibration_monthly_due_notify'),
    path('notifications/delete/<int:notif_id>/', views.notification_delete, name='notification_delete'),
    path('references-admin/cert-file/<int:file_id>/delete/', views.ref_cert_file_delete, name='ref_cert_file_delete'),
    path('references-admin/cert-file/<int:file_id>/move/', views.ref_cert_file_move, name='ref_cert_file_move'),
    path('references-admin/certificate/<int:cert_id>/append/', views.ref_cert_append_files, name='ref_cert_append_files'),
    path('references-admin/cert-file/<int:file_id>/view/', views.ref_cert_file_view, name='ref_cert_file_view'),
]

# ===== Calibration Verification URLs =====
from . import views_verification as vv

urlpatterns += [
    path('calibration/verification/', vv.verification_list, name='calibration_verification_list'),
    path('calibration/verification/dashboard/', vv.verification_dashboard, name='calibration_verification_dashboard'),
    path('calibration/verification/new/', vv.verification_create, name='calibration_verification_create'),
    path('calibration/verification/new/<str:equipment_code>/', vv.verification_create, name='calibration_verification_create_eq'),
    path('calibration/verification/<int:pk>/', vv.verification_detail, name='calibration_verification_detail'),
    path('calibration/verification/<int:pk>/print/', vv.verification_print, name='calibration_verification_print'),
    path('calibration/verification/<int:pk>/reactivate/', vv.verification_reactivate, name='calibration_verification_reactivate'),
    path('api/verification/rules/<str:code>/', vv.api_rules_for_equipment, name='api_verification_rules'),
    path('api/verification/equipment-lookup/', vv.api_equipment_lookup, name='api_verification_equipment_lookup'),
]

urlpatterns += [
    path('calibration/verification/preview/', vv.verification_preview, name='calibration_verification_preview'),
]

urlpatterns += [path('api/verification/equipment/<str:code>/', vv.api_equipment_info, name='api_verification_equipment_info')]

urlpatterns += [path('api/verification/suggestions/<str:code>/', vv.api_equipment_suggestions, name='api_verification_suggestions')]

urlpatterns += [
    path('calibration/verification/<int:pk>/edit/', vv.verification_edit, name='calibration_verification_edit'),
]

urlpatterns += [
    path('operator/delete-image/<int:img_id>/', views.delete_sample_image, name='delete_sample_image'),
]

# ===== PRINT REPORT=====
path('reports/print-overlay/<int:req_id>/', views.print_overlay_form, name='print_overlay_form'),
urlpatterns += [
    ]

urlpatterns += [
    path('api/report-suggestions/', views.api_report_suggestions, name='api_report_suggestions'),
]

urlpatterns += [
    path('reports/final-print/<int:req_id>/', views.final_report_print, name='final_report_print'),
]
