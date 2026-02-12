from openpyxl import load_workbook
from pathlib import Path
from django.conf import settings
from customer_management.models import Customer
from dvadmin.system.models import Users

base_dir = Path(settings.BASE_DIR)
path = base_dir.parent.parent / 'dev_doc' / 'import_temp.xlsx'
print('loading', path)
wb = load_workbook(path)
ws = wb.active
rows = list(ws.values)
updated = 0
missing_user = []
missing_customer = []
for row in rows[1:]:
    if not row or not row[1]:
        continue
    customer_name = str(row[1]).strip()
    owner_text = row[12] if len(row) > 12 else None
    if not owner_text:
        continue
    owner_text = str(owner_text).strip()
    if ' - ' in owner_text:
        name_part = owner_text.split(' - ',1)[1].strip()
    else:
        name_part = owner_text
    owner = Users.objects.filter(name=name_part, is_active=True).first() or Users.objects.filter(username=name_part, is_active=True).first()
    if not owner:
        missing_user.append((customer_name, owner_text))
        continue
    cust = Customer.objects.filter(name=customer_name, is_deleted=False).first()
    if not cust:
        missing_customer.append(customer_name)
        continue
    cust.owner_user = owner
    cust.owner_user_name = owner.name or owner.username
    cust.save(update_fields=['owner_user','owner_user_name','update_datetime'])
    updated +=1
print('updated', updated)
print('missing_user', len(missing_user))
if missing_user:
    print(missing_user[:20])
print('missing_customer', len(missing_customer))
if missing_customer:
    print(missing_customer[:20])
