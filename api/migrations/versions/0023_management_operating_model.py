"""E.Y.T management operating model: positions, ownership, KPIs and segregation of duties.
Revision ID: 0023
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("org_positions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("title_fa", sa.String(200), nullable=False),
        sa.Column("mission_fa", sa.Text(), nullable=False),
        sa.Column("reports_to_code", sa.String(80)),
        sa.Column("process_owner", sa.String(160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_org_positions_active","org_positions",["is_active","code"])

    op.create_table("org_kpis",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("position_code",sa.String(80),nullable=False),
        sa.Column("code",sa.String(100),nullable=False,unique=True),
        sa.Column("title_fa",sa.String(200),nullable=False),
        sa.Column("metric_key",sa.String(120),nullable=False),
        sa.Column("target_rule",sa.String(500)),
        sa.Column("frequency",sa.String(20),nullable=False,server_default="MONTHLY"),
        sa.Column("weight",sa.Numeric(6,2),nullable=False,server_default="1"),
        sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.text("TRUE")),
        sa.ForeignKeyConstraint(["position_code"],["org_positions(code)"],ondelete="CASCADE"),
    )
    op.create_index("idx_org_kpis_position","org_kpis",["position_code","is_active"])

    op.create_table("org_employee_assignments",
        sa.Column("id",UUID(as_uuid=True),primary_key=True,server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",UUID(as_uuid=True),sa.ForeignKey("eyt_users.id",ondelete="CASCADE"),nullable=False),
        sa.Column("position_code",sa.String(80),sa.ForeignKey("org_positions(code)",ondelete="RESTRICT"),nullable=False),
        sa.Column("location_code",sa.String(80)),
        sa.Column("starts_at",sa.Date(),nullable=False,server_default=sa.text("CURRENT_DATE")),
        sa.Column("ends_at",sa.Date()),
        sa.Column("is_primary",sa.Boolean(),nullable=False,server_default=sa.text("TRUE")),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("ends_at IS NULL OR ends_at >= starts_at",name="ck_org_assignment_dates"),
    )
    op.create_index("idx_org_assignment_user_active","org_employee_assignments",["user_id","is_primary","ends_at"])

    op.create_table("org_sod_rules",
        sa.Column("id",UUID(as_uuid=True),primary_key=True,server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_code",sa.String(100),nullable=False,unique=True),
        sa.Column("title_fa",sa.String(200),nullable=False),
        sa.Column("description_fa",sa.Text(),nullable=False),
        sa.Column("risk_level",sa.String(20),nullable=False,server_default="HIGH"),
        sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.text("TRUE")),
        sa.CheckConstraint("risk_level IN ('MEDIUM','HIGH','CRITICAL')",name="ck_org_sod_risk"),
    )

    positions=[
      ("CEO","مدیرعامل","جهت‌دهی، طراحی سیستم، تخصیص منابع و کنترل نتایج؛ نه اجرای روزانه.",None,"استراتژی و کنترل کل شرکت"),
      ("SYSTEM_DEV","مدیر سیستم و توسعه","طراحی و بهبود فرآیندها، ERP، AI، اتوماسیون، داده و KPI.","CEO","سیستم و توسعه"),
      ("ENGINEERING_PRODUCT","مدیر مهندسی و محصول","مالک Product Master، SKU، BOM، نقشه، استاندارد و تغییرات محصول.","CEO","مهندسی و محصول"),
      ("PRODUCTION","مدیر تولید","مالک برنامه، ظرفیت، اجرای تولید و عملکرد کارگاه‌ها.","CEO","تولید"),
      ("QC","مسئول کنترل و تضمین کیفیت","مالک استاندارد کیفیت، بازرسی، NCR، قرنطینه و آزادسازی محصول.","CEO","کیفیت"),
      ("PROCUREMENT","مدیر تأمین و خرید","مالک تأمین مواد و قطعات، سفارش خرید و ارزیابی تأمین‌کننده.","CEO","تأمین"),
      ("WAREHOUSE_LOGISTICS","مدیر انبار و لجستیک","مالک دریافت، نگهداری، انتقال، موجودی، Picking، Packing و ارسال.","CEO","انبار و لجستیک"),
      ("SALES_COMMERCIAL","مدیر فروش و بازرگانی","مالک فروش B2B، نمایندگان، مشتریان تجاری، قیمت فروش و سفارش.","CEO","فروش و بازرگانی"),
      ("DIGITAL_COMMERCE","مدیر کانال‌های دیجیتال و تجارت الکترونیک","مالک Click One، سایت، شبکه‌های اجتماعی، SMS، CRM و فروش B2C.","SALES_COMMERCIAL","تجارت دیجیتال"),
      ("FINANCE","مدیر مالی و کنترل منابع","مالک نقدینگی، وصول، پرداخت، هزینه، سود واقعی و کنترل مالی.","CEO","مالی"),
      ("HR","مدیر منابع انسانی","مالک جذب، ارزیابی، آموزش، جبران خدمت، انضباط و جانشینی.","CEO","منابع انسانی"),
      ("ADMIN","مدیر اداری و پشتیبانی","مالک قراردادها، اسناد، بیمه، ساختمان و خدمات پشتیبانی.","CEO","اداری"),
      ("TABRIZ_WORKSHOP","سرپرست تولید و مونتاژ تبریز","اجرای برنامه تولید، مونتاژ، جوشکاری، ثبت تولید و تحویل به QC.","PRODUCTION","کارگاه تبریز"),
      ("ISFAHAN_RUBBER","مسئول توسعه و تولید لاستیک و بوش اصفهان","توسعه قالب، مواد، نمونه و تولید پایدار محصولات لاستیکی.","PRODUCTION","کارگاه اصفهان"),
      ("PLATING","مسئول اجرای آبکاری","اجرای فرآیند آبکاری، ثبت پارت و تحویل برای QC.","PRODUCTION","آبکاری"),
      ("TEHRAN_SHOP_ACCOUNTING","مسئول مغازه تهران و حسابداری شرکت","اجرای فروش مغازه، ثبت حسابداری و کنترل عملیاتی؛ بدون تمرکز کامل چرخه پرداخت.","FINANCE","تهران"),
    ]
    for code,title,mission,reports,owner in positions:
        op.execute(sa.text("""INSERT INTO org_positions(code,title_fa,mission_fa,reports_to_code,process_owner)
VALUES (:code,:title,:mission,:reports,:owner)
ON CONFLICT (code) DO UPDATE SET title_fa=EXCLUDED.title_fa,mission_fa=EXCLUDED.mission_fa,
reports_to_code=EXCLUDED.reports_to_code,process_owner=EXCLUDED.process_owner,is_active=TRUE"""),
          dict(code=code,title=title,mission=mission,reports=reports,owner=owner))

    kpis=[
      ("CEO","CEO_CASH","نقدینگی قابل دسترس","cash_available","مثبت و مطابق برنامه نقدینگی","DAILY",2),
      ("CEO","CEO_PROFIT","سود واقعی","realized_profit","مثبت و رو به رشد","MONTHLY",3),
      ("SYSTEM_DEV","SYS_AUTOMATION","درصد فرآیندهای بدون ورود دستی","automation_rate","رشد ماهانه","MONTHLY",2),
      ("PRODUCTION","PROD_PLAN_ATTAIN","تحقق برنامه تولید","production_plan_attainment_pct",">=95","DAILY",3),
      ("PRODUCTION","PROD_SCRAP","نرخ ضایعات","scrap_rate_pct","<=هدف محصول","WEEKLY",2),
      ("QC","QC_RELEASE","درصد آزادسازی بدون NCR","qc_first_pass_release_pct",">=98","WEEKLY",3),
      ("PROCUREMENT","PURCHASE_OTIF","تحویل به‌موقع خرید","supplier_otif_pct",">=95","MONTHLY",2),
      ("WAREHOUSE_LOGISTICS","INV_ACCURACY","دقت موجودی","inventory_accuracy_pct",">=99","WEEKLY",3),
      ("SALES_COMMERCIAL","B2B_COLLECTION","وصول فروش B2B","b2b_collection_rate_pct",">=80","WEEKLY",3),
      ("DIGITAL_COMMERCE","B2C_CONVERSION","نرخ تبدیل B2C","b2c_conversion_pct","هدف کانال","WEEKLY",2),
      ("FINANCE","FIN_CASH_CONTROL","انحراف نقدینگی","cash_variance_pct","<=2","DAILY",3),
      ("FINANCE","FIN_AR_OVERDUE","مطالبات سررسید گذشته","overdue_receivable_amount","کاهشی","WEEKLY",3),
      ("TABRIZ_WORKSHOP","TABRIZ_OUTPUT","تحقق تولید کارگاه تبریز","production_plan_attainment_pct",">=95","DAILY",3),
      ("ISFAHAN_RUBBER","ISFAHAN_OUTPUT","تحقق تولید اصفهان","production_plan_attainment_pct",">=95","WEEKLY",3),
      ("PLATING","PLATING_BATCH","پارت آبکاری تکمیل‌شده","plating_batches_completed","طبق برنامه","DAILY",2),
      ("TEHRAN_SHOP_ACCOUNTING","SHOP_RECON","تطبیق فروش و وجه","shop_cash_reconciliation_pct","=100","DAILY",3),
    ]
    for pos,code,title,metric,target,freq,weight in kpis:
        op.execute(sa.text("""INSERT INTO org_kpis(position_code,code,title_fa,metric_key,target_rule,frequency,weight)
VALUES (:pos,:code,:title,:metric,:target,:freq,:weight)
ON CONFLICT (code) DO UPDATE SET position_code=EXCLUDED.position_code,title_fa=EXCLUDED.title_fa,
metric_key=EXCLUDED.metric_key,target_rule=EXCLUDED.target_rule,frequency=EXCLUDED.frequency,
weight=EXCLUDED.weight,is_active=TRUE"""),
          dict(pos=pos,code=code,title=title,metric=metric,target=target,freq=freq,weight=weight))

    rules=[
      ("SOD_QC_PRODUCTION","تأیید کیفیت مستقل از تولید","تولیدکننده نباید آزادسازی نهایی همان محصول/پارت را انجام دهد.","CRITICAL"),
      ("SOD_PURCHASE_PAYMENT","تفکیک خرید و پرداخت","ایجاد درخواست خرید، تأیید و پرداخت نباید در اختیار یک نفر باشد.","CRITICAL"),
      ("SOD_SALES_COLLECTION","تفکیک فروش و وصول","ثبت فروش و تأیید نهایی وصول/تطبیق بانکی باید قابل تفکیک باشد.","HIGH"),
      ("SOD_DIGITAL_MASTERDATA","تفکیک کانال دیجیتال و Master Data","مدیر کانال دیجیتال حق تغییر مستقل Product Master، موجودی حقیقت یا قیمت پایه را ندارد.","HIGH"),
      ("SOD_DOCUMENT_ACCOUNTING","تفکیک ورود سند و ثبت نهایی مالی","OCR/ورود سند باید قبل از ثبت قطعی حسابداری قابل کنترل باشد.","HIGH"),
    ]
    for code,title,desc,risk in rules:
        op.execute(sa.text("""INSERT INTO org_sod_rules(rule_code,title_fa,description_fa,risk_level)
VALUES (:code,:title,:desc,:risk)
ON CONFLICT (rule_code) DO UPDATE SET title_fa=EXCLUDED.title_fa,
description_fa=EXCLUDED.description_fa,risk_level=EXCLUDED.risk_level,is_active=TRUE"""),
          dict(code=code,title=title,desc=desc,risk=risk))

def downgrade():
    op.drop_table("org_sod_rules")
    op.drop_index("idx_org_assignment_user_active",table_name="org_employee_assignments")
    op.drop_table("org_employee_assignments")
    op.drop_index("idx_org_kpis_position",table_name="org_kpis")
    op.drop_table("org_kpis")
    op.drop_index("idx_org_positions_active",table_name="org_positions")
    op.drop_table("org_positions")
