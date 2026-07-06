#!/usr/bin/env python3
"""
AMIS CRM ↔ MISA Comprehensive Audit Report Generator
Cross-references all 5 input files, detects discrepancies, outputs Excel report.
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from collections import defaultdict, Counter
from datetime import datetime, date
from pathlib import Path
import re, sys, textwrap

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'input'
OLD_CHECK = ROOT / 'old_check'
TODAY = date(2026, 7, 5)  # Snapshot date

# ============================================================
# 1. LOAD DATA
# ============================================================

print("[1/5] Loading CRM_Sale.xlsx...", file=sys.stderr)

crm_orders = {}  # order_id -> dict
crm_lineitems = defaultdict(list)  # order_id -> list of line items

wb = openpyxl.load_workbook(f'{BASE}/CRM_Sale.xlsx', read_only=True, data_only=True)

ws = wb['Danh sách']
crm_headers = [str(c.value) if c.value is not None else f'COL{i}' for i, c in enumerate(ws[1])]
# Build header index
crm_h = {h: i for i, h in enumerate(crm_headers)}

row_count = 0
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0] is None:
        continue
    oid = str(row[0]).strip()
    rec = {}
    for hdr, idx in crm_h.items():
        rec[hdr] = row[idx]
    crm_orders[oid] = rec
    row_count += 1

print(f"   CRM Danh sách: {row_count} orders loaded", file=sys.stderr)

# Load line items
ws2 = wb['Bảng hàng hóa']
li_headers = [str(c.value) if c.value is not None else f'COL{i}' for i, c in enumerate(ws2[1])]
li_h = {h: i for i, h in enumerate(li_headers)}
li_count = 0
for row in ws2.iter_rows(min_row=2, values_only=True):
    if row[0] is None:
        continue
    oid = str(row[0]).strip()
    rec = {}
    for hdr, idx in li_h.items():
        rec[hdr] = row[idx]
    crm_lineitems[oid].append(rec)
    li_count += 1
print(f"   CRM Bảng hàng hóa: {li_count} line items loaded", file=sys.stderr)
wb.close()

# ============================================================

print("[2/5] Loading MISA_Accounting.xlsx...", file=sys.stderr)

misa_orders = {}
wb = openpyxl.load_workbook(f'{BASE}/MISA_Accounting.xlsx', read_only=True, data_only=True)
ws = wb['Đơn đặt hàng']
misa_headers = [str(c.value) if c.value is not None else f'COL{i}' for i, c in enumerate(ws[3])]
misa_h = {h: i for i, h in enumerate(misa_headers)}
misa_count = 0
for row in ws.iter_rows(min_row=4, values_only=True):
    if row[misa_h['Số đơn hàng']] is None:
        continue
    oid = str(row[misa_h['Số đơn hàng']]).strip()
    rec = {}
    for hdr, idx in misa_h.items():
        rec[hdr] = row[idx]
    misa_orders[oid] = rec
    misa_count += 1
print(f"   MISA: {misa_count} orders loaded", file=sys.stderr)
wb.close()

# ============================================================

print("[3/5] Loading So_chi_tiet_ban_hang.xlsx...", file=sys.stderr)

so_orders = defaultdict(list)  # order_id -> list of invoice lines
so_invoice_map = defaultdict(set)  # order_id -> set of invoice numbers

wb = openpyxl.load_workbook(f'{BASE}/So_chi_tiet_ban_hang.xlsx', read_only=True, data_only=True)
ws = wb['SỔ CHI TIẾT BÁN HÀNG']
so_headers = [str(c.value) if c.value is not None else f'COL{i}' for i, c in enumerate(ws[4])]
so_h = {h: i for i, h in enumerate(so_headers)}
so_row_count = 0
dh_in_so_col = set()
for row in ws.iter_rows(min_row=5, values_only=True):
    so_row_count += 1
    # Try col 29 first
    oid = str(row[28]).strip() if row[28] else ''
    desc = str(row[8]).strip() if row[8] else ''
    
    if not oid:
        # Try extracting from description: "Đơn hàng bán DH-xxxx"
        m = re.search(r'DH-\d+', desc)
        if m:
            oid = m.group(0)
    
    if oid and oid.startswith('DH-'):
        dh_in_so_col.add(oid)
        rec = {}
        for hdr, idx in so_h.items():
            rec[hdr] = row[idx]
        so_orders[oid].append(rec)
        inv_num = str(row[7]).strip() if row[7] else ''
        if inv_num:
            so_invoice_map[oid].add(inv_num)

print(f"   So_chi_tiet: {so_row_count} rows, {len(dh_in_so_col)} unique DH- orders", file=sys.stderr)
print(f"   Orders with invoices: {len(so_invoice_map)}", file=sys.stderr)
wb.close()

# ============================================================

print("[4/5] Loading Pre order feedback...", file=sys.stderr)

pre_orders = {}
pre_lines = defaultdict(list)
wb = openpyxl.load_workbook(f'{BASE}/Pre order feedback.xlsx', read_only=True, data_only=True)
ws = wb['Pre-orders']
pre_headers = [str(c.value) if c.value is not None else f'COL{i}' for i, c in enumerate(ws[1])]
pre_h = {h: i for i, h in enumerate(pre_headers)}

for row in ws.iter_rows(min_row=2, values_only=True):
    if row[pre_h['ĐH']] is None:
        continue
    oid = str(row[pre_h['ĐH']]).strip()
    note = str(row[pre_h['Note']]).strip() if row[pre_h['Note']] else ''
    hangiao = str(row[pre_h['HẠN GIAO HÀNG']])[:10] if row[pre_h['HẠN GIAO HÀNG']] else ''
    
    if oid not in pre_orders:
        pre_orders[oid] = {
            'note_actions': set(),
            'is_pending': False,
            'is_resolved': False,
            'hangiao': hangiao,
            'total_rev': 0,
        }
    if note:
        pre_orders[oid]['note_actions'].add(note)
    pre_orders[oid]['hangiao'] = hangiao
    if row[pre_h['NET REV SOLD']]:
        pre_orders[oid]['total_rev'] += float(row[pre_h['NET REV SOLD']])

for oid, info in pre_orders.items():
    has_pending = any('Pre order' in n for n in info['note_actions'])
    has_revenue = any('ghi nhận' in n for n in info['note_actions'])
    has_action = any(n not in ('Pre order', 'Đã ghi nhận ở revenue', '') for n in info['note_actions'])
    info['is_pending'] = has_pending and not has_revenue
    info['is_resolved'] = has_revenue and not has_pending and not has_action
    info['needs_action'] = has_action

print(f"   Pre-order: {len(pre_orders)} unique orders", file=sys.stderr)
wb.close()

# ============================================================

print("[5/5] Loading Master audit CSV...", file=sys.stderr)

master_orders = {}
with open(f'{OLD_CHECK}/danh_sach_toan_bo_don_hang_review_nhom_loi_huong_xu_ly.csv', 'r', encoding='utf-8-sig') as f:
    master_headers_raw = f.readline().strip().split(',')
    master_headers = [h.strip('"') for h in master_headers_raw]
    # Build header index (case-insensitive, strip quotes)
    master_h = {}
    for i, h in enumerate(master_headers):
        master_h[h.lower().strip()] = i
    
    for line in f:
        parts = line.strip().split(',')
        # Find order_id column
        oid_col = master_h.get('order_id', 0)
        if oid_col >= len(parts):
            continue
        oid = parts[oid_col].strip('"').strip()
        if not oid:
            continue
        rec = {}
        for hdr, idx in master_h.items():
            if idx < len(parts):
                rec[hdr] = parts[idx].strip('"')
        master_orders[oid] = rec

print(f"   Master: {len(master_orders)} orders loaded", file=sys.stderr)

# ============================================================
# 1b. LOAD CRM_Activities
# ============================================================

print("[1b] Loading CRM_Activities.xlsx...", file=sys.stderr)

activity_orders = defaultdict(list)  # order_id -> list of activities
activity_types = Counter()

wb = openpyxl.load_workbook(f'{BASE}/CRM_Activities.xlsx', read_only=True, data_only=True)
ws = wb['Danh sách']
act_headers = [str(c.value) if c.value is not None else f'COL{i}' for i, c in enumerate(ws[1])]
act_h = {h: i for i, h in enumerate(act_headers)}

act_count = 0
for row in ws.iter_rows(min_row=2, values_only=True):
    # Liên quan đến = col 6
    ref = str(row[6]).strip() if row[6] else ''
    if not ref:
        continue
    # Extract DH-xxx from "Liên quan đến" field
    oids = re.findall(r'DH-\d+', ref)
    if not oids:
        continue
    act_type = str(row[0]).strip() if row[0] else ''
    activity_types[act_type] += 1
    
    rec = {}
    for hdr, idx in act_h.items():
        rec[hdr] = row[idx]
    
    for oid in oids:
        activity_orders[oid].append(rec)
    act_count += 1

print(f"   Activities: {act_count} loaded, types: {dict(activity_types.most_common())}", file=sys.stderr)
wb.close()


# ============================================================
# 2. DETECTION RULES
# ============================================================

print("\nRunning detection rules...", file=sys.stderr)

discrepancies = []
disc_id = [0]  # mutable counter

def add_disc(discrepancy_type, severity, order_id, crm_status, misa_status, detail, 
             source_files='', suggestion='', old_group='', priority=''):
    disc_id[0] += 1
    disc = {
        'id': disc_id[0],
        'type': discrepancy_type,
        'severity': severity,
        'order_id': order_id,
        'customer': crm_orders.get(order_id, {}).get('Khách hàng', ''),
        'owner': crm_orders.get(order_id, {}).get('Người thực hiện', ''),
        'gioi_doan': crm_orders.get(order_id, {}).get('Giai đoạn', ''),
        'CRM_delivery': str(crm_status.get('delivery', '')),
        'CRM_payment': str(crm_status.get('payment', '')),
        'CRM_accounting': str(crm_status.get('accounting', '')),
        'CRM_approval': str(crm_status.get('approval', '')),
        'CRM_execution': str(crm_status.get('execution', '')),
        'CRM_invoiced': str(crm_status.get('invoiced', '')),
        'CRM_invoice_value': str(crm_status.get('invoice_value', '')),
        'MISA_delivery': str(misa_status.get('delivery', '')),
        'MISA_payment': str(misa_status.get('payment', '')),
        'MISA_accounting': str(misa_status.get('accounting', '')),
        'MISA_invoiced': str(misa_status.get('invoiced', '')),
        'MISA_invoice_value': str(misa_status.get('invoice_value', '')),
        'MISA_thuc_thu': str(misa_status.get('thuc_thu', '')),
        'MISA_con_thu': str(misa_status.get('con_thu', '')),
        'MISA_delivery_date': str(misa_status.get('delivery_date', '')),
        'detail': detail,
        'source_files': source_files,
        'suggestion': suggestion,
        'old_group': old_group,
        'owner_chinh': '',
    }
    discrepancies.append(disc)

# Common helper
def val(v):
    """Safely convert value to string"""
    if v is None:
        return ''
    return str(v).strip()

def float_val(v):
    """Convert to float, return 0 if None/empty"""
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0

# ============================================================

# Collect ALL order IDs across all sources
all_order_ids = set(crm_orders.keys()) | set(misa_orders.keys()) | set(so_orders.keys()) | set(pre_orders.keys()) | set(master_orders.keys())
print(f"Total unique orders across all sources: {len(all_order_ids)}", file=sys.stderr)

# Status values
DELIVERY_DELIVERED = {'Đã giao hàng', 'Đã giao'}
DELIVERY_DELIVERING = {'Đang giao hàng'}
DELIVERY_NOT_DELIVERED = {'Chưa giao hàng', ''}
PAID = {'Đã thanh toán', 'Đã thanh toán một phần'}
NOT_PAID = {'Chưa thanh toán', ''}
REJECTED = {'Từ chối ghi'}
DRAFT = {'Bản nháp'}
SUBMITTED = {'Đề nghị ghi'}
APPROVED = {'Đã duyệt'}

def parse_iso_date(raw):
    """Parse YYYY-MM-DD-like strings from Excel values."""
    text = val(raw)
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], '%Y-%m-%d').date()
    except ValueError:
        return None

def is_reportable_crm_order(accounting_status, approval_status):
    """Orders worth reporting: submitted for accounting or approved, excluding drafts/rejections."""
    if accounting_status in DRAFT or accounting_status in REJECTED:
        return False
    return accounting_status in SUBMITTED or approval_status in APPROVED

loop_count = 0
for oid in sorted(all_order_ids):
    loop_count += 1
    if loop_count % 1000 == 0:
        print(f"   Processing: {loop_count}/{len(all_order_ids)}", file=sys.stderr)
    
    crm = crm_orders.get(oid, {})
    misa = misa_orders.get(oid, {})
    pre = pre_orders.get(oid, {})
    master = master_orders.get(oid, {})
    activities = activity_orders.get(oid, [])
    
    crm_stage = val(crm.get('Giai đoạn', ''))
    
    # CRM status values
    crm_delivery = val(crm.get('Tình trạng giao hàng', ''))
    crm_payment = val(crm.get('Tình trạng thanh toán', ''))
    crm_accounting = val(crm.get('Tình trạng ghi doanh số', ''))
    crm_approval = val(crm.get('Trạng thái phê duyệt', ''))
    crm_execution = val(crm.get('Tình trạng', ''))
    crm_invoiced = val(crm.get('Đã xuất hóa đơn', ''))
    crm_inv_val = float_val(crm.get('Giá trị đã xuất hóa đơn', ''))
    crm_con_thu = float_val(crm.get('Còn phải thu', ''))
    crm_gia_tri = float_val(crm.get('Giá trị đơn hàng', ''))
    
    # MISA status values
    misa_delivery = val(misa.get('Tình trạng giao hàng', ''))
    misa_payment_thucthu = float_val(misa.get('Thực thu', ''))
    misa_con_thu = float_val(misa.get('Số còn phải thu', ''))
    misa_accounting = val(misa.get('Tình trạng ghi doanh số', ''))
    misa_invoiced = val(misa.get('Tình trạng xuất hóa đơn', ''))
    misa_inv_val = float_val(misa.get('Giá trị đã xuất hóa đơn', ''))
    misa_delivery_date = val(misa.get('Ngày giao hàng', ''))
    misa_hangiao = val(misa.get('Hạn giao hàng', ''))
    misa_status = val(misa.get('Tình trạng', ''))
    misa_gia_tri = float_val(misa.get('Giá trị đơn hàng', ''))
    is_reportable = oid not in crm_orders or is_reportable_crm_order(crm_accounting, crm_approval)
    
    # So_chi_tiet data
    so_lines = so_orders.get(oid, [])
    so_invoices = so_invoice_map.get(oid, set())
    so_total = sum(float_val(r.get('Doanh số bán', 0)) for r in so_lines)
    so_has_invoice = len(so_invoices) > 0 or len(so_lines) > 0
    
    # Activities
    has_nvgh = any('Xác nhận giao hàng' in val(a.get('Loại nhiệm vụ', '')) for a in activities)
    has_payment_confirm = any('Xác nhận thanh toán' in val(a.get('Loại nhiệm vụ', '')) for a in activities)
    
    # Old master classification
    old_group = master.get('primary_issue_group', '')
    old_priority = master.get('priority', '')
    old_comment = master.get('review_comment', '')
    
    # CRM status struct for add_disc
    crm_status = {
        'delivery': crm_delivery,
        'payment': crm_payment,
        'accounting': crm_accounting,
        'approval': crm_approval,
        'execution': crm_execution,
        'invoiced': crm_invoiced,
        'invoice_value': crm_inv_val,
    }
    misa_status = {
        'delivery': misa_delivery,
        'payment': '' if misa_con_thu == 0 and misa_payment_thucthu == 0 else f'Thực thu={misa_payment_thucthu:,.0f}',
        'accounting': misa_accounting,
        'invoiced': misa_invoiced,
        'invoice_value': misa_inv_val,
        'thuc_thu': f'{misa_payment_thucthu:,.0f}' if misa_payment_thucthu else '0',
        'con_thu': f'{misa_con_thu:,.0f}',
        'delivery_date': misa_delivery_date,
    }
    
    # --- RULE A: CRM-only orders (not in MISA at all) ---
    if oid not in misa_orders and is_reportable:
        add_disc('A-Missing_MISA', 'HIGH', oid, crm_status, {'delivery': 'NOT_IN_MISA'},
                 f"Đơn có trên CRM (ghi DS='{crm_accounting}', duyệt='{crm_approval}') nhưng KHÔNG có trên MISA",
                 source_files='CRM_Sale',
                 suggestion='Kiểm tra đồng bộ CRM→MISA. Có thể đơn chưa được duyệt hoặc chưa sync.',
                 old_group=old_group)
    
    # --- RULE A2: MISA-only orders (not in CRM) ---
    # Skip CKHO-* (chứng từ kho, internal warehouse, not sales orders)
    if oid.startswith('CKHO'):
        pass
    elif oid not in crm_orders:
        add_disc('A2-Missing_CRM', 'HIGH', oid, {'delivery': 'NOT_IN_CRM'}, misa_status,
                 f"Đơn có trên MISA nhưng KHÔNG có trên CRM",
                 source_files='MISA_Accounting',
                 suggestion='Kiểm tra đồng bộ MISA→CRM. Có thể xóa trên CRM nhưng MISA còn.')
    
    # --- RULE B: Delivery status mismatch ---
    if is_reportable and crm_delivery in DELIVERY_DELIVERED and misa_delivery not in DELIVERY_DELIVERED and misa_delivery:
        add_disc('B-Delivery_Mismatch', 'HIGH', oid, crm_status, misa_status,
                 f"CRM: '{crm_delivery}' nhưng MISA: '{misa_delivery}'",
                 source_files='CRM_Sale+MISA_Accounting',
                 suggestion='Kiểm tra trạng thái giao hàng thực tế. Nếu MISA chưa giao, CRM đang sai.',
                 old_group=old_group)
    
    if is_reportable and crm_delivery not in DELIVERY_DELIVERED and misa_delivery in DELIVERY_DELIVERED and misa_delivery_date:
        add_disc('B2-Delivery_Mismatch', 'MEDIUM', oid, crm_status, misa_status,
                 f"MISA đã giao ({misa_delivery_date}) nhưng CRM: '{crm_delivery}'",
                 source_files='CRM_Sale+MISA_Accounting',
                 suggestion='CRM chưa cập nhật trạng thái giao hàng. Cần sales update.',
                 old_group=old_group)
    
    # --- RULE C: Payment mismatch ---
    if is_reportable and crm_payment in PAID and misa_payment_thucthu == 0 and misa_gia_tri > 0:
        add_disc('C-Payment_Mismatch', 'HIGH', oid, crm_status, misa_status,
                 f"CRM: '{crm_payment}', MISA Thực thu={misa_payment_thucthu:,.0f}",
                 source_files='CRM_Sale+MISA_Accounting',
                 suggestion='CRM nói đã thanh toán nhưng MISA không thấy tiền. Kiểm tra TK cá nhân hoặc sai sót.',
                 old_group=old_group)
    
    if is_reportable and crm_payment in NOT_PAID and misa_payment_thucthu > 0 and crm_gia_tri > 0:
        add_disc('C2-Payment_Mismatch', 'MEDIUM', oid, crm_status, misa_status,
                 f"CRM: '{crm_payment}' nhưng MISA Thực thu={misa_payment_thucthu:,.0f}",
                 source_files='CRM_Sale+MISA_Accounting',
                 suggestion='CRM chưa cập nhật thanh toán. Kiểm tra và update.',
                 old_group=old_group)
    
    # --- RULE D: Accounting record mismatch ---
    # Skip if CRM is still in draft (not yet submitted for processing)
    if not is_reportable:
        pass
    elif crm_accounting and misa_accounting and crm_accounting != misa_accounting:
        add_disc('D-Accounting_Mismatch', 'HIGH', oid, crm_status, misa_status,
                 f"CRM: '{crm_accounting}' vs MISA: '{misa_accounting}'",
                 source_files='CRM_Sale+MISA_Accounting',
                 suggestion='Lệch trạng thái ghi doanh số. Cần đồng bộ.',
                 old_group=old_group)
    
    # --- RULE E: Invoice mismatch ---
    if is_reportable and crm_invoiced and not so_has_invoice:
        add_disc('E-Invoice_Mismatch', 'HIGH', oid, crm_status, misa_status,
                 f"CRM: '{crm_invoiced}' (value={crm_inv_val:,.0f}) nhưng không có trong Sổ chi tiết bán hàng",
                 source_files='CRM_Sale+So_chi_tiet_ban_hang',
                 suggestion='CRM đã xuất hóa đơn nhưng không tìm thấy trong MISA Sổ chi tiết. Kiểm tra chứng từ.',
                 old_group=old_group)
    
    if is_reportable and so_has_invoice and not crm_invoiced:
        add_disc('E2-Invoice_Mismatch', 'MEDIUM', oid, crm_status, misa_status,
                 f"Có trong Sổ chi tiết bán hàng ({len(so_lines)} dòng, invoices={so_invoices}) nhưng CRM không ghi nhận xuất hóa đơn",
                 source_files='CRM_Sale+So_chi_tiet_ban_hang',
                 suggestion='MISA đã có hóa đơn nhưng CRM chưa cập nhật. Cần đồng bộ.',
                 old_group=old_group)
    
    # --- RULE F: Rejected orders ---
    # Business decision: rejected accounting orders are excluded from the active issue report.
    
    # --- RULE G: Overdue delivery ---
    hg_date = parse_iso_date(misa_hangiao)
    if is_reportable and hg_date and hg_date < TODAY and crm_delivery not in DELIVERY_DELIVERED:
        add_disc('G-Overdue', 'MEDIUM', oid, crm_status, misa_status,
                 f"Quá hạn giao: Hạn={misa_hangiao[:10]}, quá {(TODAY - hg_date).days} ngày, vẫn '{crm_delivery}'",
                 source_files='MISA_Accounting+CRM_Sale',
                 suggestion='Đơn quá hạn giao hàng. Cần xác nhận lý do chậm và cập nhật ETA.',
                 old_group=old_group)
    
    # --- RULE H: Pre-order specific ---
    if pre:
        if pre.get('needs_action'):
            action_notes = [n for n in pre['note_actions'] if n not in ('Pre order', 'Đã ghi nhận ở revenue', '')]
            detail = '; '.join(action_notes[:3])
            if len(action_notes) > 3:
                detail += f' (+{len(action_notes)-3} more)'
            add_disc('H-Preorder_Action', 'MEDIUM', oid, crm_status, misa_status,
                     f"Pre-order cần xử lý: {detail}",
                     source_files='Pre order feedback',
                     suggestion='Xem chi tiết trong sheet Pre-order Issues.',
                     old_group=old_group)
    
    # --- RULE I: NVGH but delivery still open (G1 check) ---
    if is_reportable and has_nvgh and crm_delivery not in DELIVERY_DELIVERED:
        add_disc('I-NVGH_Activity_Open_Delivery', 'LOW', oid, crm_status, misa_status,
                 f"Có activity NVGH nhưng CRM delivery vẫn '{crm_delivery}'",
                 source_files='CRM_Activities+CRM_Sale',
                 suggestion='NVGH chỉ là activity xác nhận, không tự đóng delivery. Kiểm tra thực tế rồi cập nhật trạng thái giao hàng nếu đã giao.',
                 old_group=old_group if old_group else 'G1')
    
    # --- RULE J: Payment confirmed but still open (G2 check) ---
    if is_reportable and crm_payment in PAID and crm_delivery not in DELIVERY_DELIVERED and hg_date and hg_date < TODAY:
        old_g2 = (old_group == 'G2')
        if old_g2 or not old_group:
            add_disc('J-Paid_Not_Delivered', 'MEDIUM', oid, crm_status, misa_status,
                     f"Đã thanh toán ({crm_payment}) nhưng quá hẹn giao {misa_hangiao[:10]} và delivery='{crm_delivery}'",
                     source_files='CRM_Sale',
                     suggestion='Chỉ flag vì đã quá hạn giao. Cần kiểm tra đã giao thực tế chưa và cập nhật delivery_status/ETA.',
                     old_group=old_group if old_group else 'G2')
    
    # --- RULE K: Old master audit unresolved check ---
    if is_reportable and old_group:
        # Check if old issues are still present
        if old_group == 'G1' and crm_delivery not in DELIVERY_DELIVERED:
            add_disc('K-Old_G1_Unresolved', 'HIGH', oid, crm_status, misa_status,
                     f"[Master cũ] G1: Có NVGH từ audit cũ nhưng delivery vẫn '{crm_delivery}'",
                     source_files='Master+CRM_Sale+CRM_Activities',
                     suggestion='Audit cũ đã phát hiện, vẫn chưa fix. Cần KT+Ops xử lý.',
                     old_group='G1')
        elif old_group == 'G2' and crm_delivery not in DELIVERY_DELIVERED:
            add_disc('K-Old_G2_Unresolved', 'HIGH', oid, crm_status, misa_status,
                     f"[Master cũ] G2: Đã TT chưa giao từ audit cũ, delivery vẫn '{crm_delivery}'",
                     source_files='Master+CRM_Sale',
                     suggestion='Audit cũ đã phát hiện, vẫn chưa fix. Cần sales update.',
                     old_group='G2')
        elif old_group == 'G7' and crm_accounting not in REJECTED:
            add_disc('K-Old_G7_MaybeFixed', 'LOW', oid, crm_status, misa_status,
                     f"[Master cũ] G7: Từng bị hủy/từ chối, nay CRM accounting='{crm_accounting}' — kiểm tra lại",
                     source_files='Master+CRM_Sale',
                     suggestion='Có thể đã được fix. Xác nhận và đóng issue.',
                     old_group='G7')
    
    # --- RULE L: Draft orders ---
    # Business decision: draft orders are excluded from this reconciliation report.
    
    # --- RULE M: CRM invoice value vs MISA invoice value ---
    if is_reportable and crm_inv_val > 0 and misa_inv_val > 0:
        diff = abs(crm_inv_val - misa_inv_val)
        if diff > 1000 and (diff / max(crm_inv_val, 0.01)) > 0.05:  # >5% diff
            add_disc('M-Invoice_Value_Mismatch', 'HIGH', oid, crm_status, misa_status,
                     f"Lệch giá trị xuất HĐ: CRM={crm_inv_val:,.0f} vs MISA={misa_inv_val:,.0f} (diff={diff:,.0f})",
                     source_files='CRM_Sale+MISA_Accounting',
                     suggestion='Giá trị hóa đơn lệch. Kiểm tra chứng từ gốc.',
                     old_group=old_group)

    # --- RULE N: No activities at all ---
    if is_reportable and len(activities) == 0 and oid in crm_orders:
        created_str = val(crm.get('Ngày tạo', ''))[:10]
        add_disc('N-No_Activity', 'LOW', oid, crm_status, misa_status,
                 f"Không có hoạt động nào (từ {created_str})",
                 source_files='CRM_Activities+CRM_Sale',
                 suggestion='Đơn không có activity. Kiểm tra đơn ma hoặc đã abandoned.',
                 old_group=old_group)

print(f"\nTotal discrepancies found: {len(discrepancies)}", file=sys.stderr)

# Compute stats
severity_counts = Counter(d['severity'] for d in discrepancies)
type_counts = Counter(d['type'] for d in discrepancies)
print(f"By severity: {dict(severity_counts)}", file=sys.stderr)
print(f"By type: {dict(type_counts.most_common())}", file=sys.stderr)

# ============================================================
# 3. GENERATE EXCEL REPORT
# ============================================================

print("\nGenerating Excel report...", file=sys.stderr)

wb_out = openpyxl.Workbook()

# --- Styles ---
header_font = Font(bold=True, color='FFFFFF', size=11)
header_fill = PatternFill(start_color='2F5496', end_color='2F5496', fill_type='solid')
header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
cell_align = Alignment(vertical='top', wrap_text=False)

red_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
yellow_fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
green_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
orange_fill = PatternFill(start_color='F4B183', end_color='F4B183', fill_type='solid')

thin_border = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin')
)

def write_sheet(ws, title, headers, rows, col_widths=None):
    """Write a data sheet with headers and rows."""
    # Headers
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
    
    # Data
    for r, row in enumerate(rows, 2):
        for c, val in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.alignment = cell_align
            cell.border = thin_border
    
    # Auto-width (not too wide)
    if col_widths:
        for c, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(c)].width = w
    else:
        for c, h in enumerate(headers, 1):
            ws.column_dimensions[get_column_letter(c)].width = min(max(len(str(h)) + 2, 15), 40)
    
    # Auto-filter
    ws.auto_filter.ref = f'A1:{get_column_letter(len(headers))}{len(rows)+1}'
    
    # Freeze top row
    ws.freeze_panes = 'A2'

# ============================================================
# Sheet 0: Tổng quan (Dashboard)
# ============================================================
ws0 = wb_out.active
ws0.title = 'Tổng quan'

# Title
ws0.merge_cells('A1:H1')
cell = ws0['A1']
cell.value = 'BÁO CÁO ĐỐI SOÁT CRM ↔ MISA'
cell.font = Font(bold=True, size=16, color='2F5496')
cell.alignment = Alignment(horizontal='center')

ws0.merge_cells('A2:H2')
ws0['A2'].value = f'Ngày snapshot: {TODAY} | Tổng số đơn kiểm tra: {len(all_order_ids)}'
ws0['A2'].font = Font(size=11, color='666666')
ws0['A2'].alignment = Alignment(horizontal='center')

# Summary stats
r = 4
summary_data = [
    ('Tổng quan dữ liệu', '', ''),
    ('Nguồn CRM Danh sách', len(crm_orders), ''),
    ('Nguồn MISA Kế toán', len(misa_orders), ''),
    ('Nguồn Sổ chi tiết bán hàng', len(so_orders), ''),
    ('Nguồn Pre-order feedback', len(pre_orders), ''),
    ('Master audit cũ', len(master_orders), ''),
    ('', '', ''),
    ('Tổng số lỗi phát hiện', len(discrepancies), ''),
    ('  HIGH', severity_counts.get('HIGH', 0), 'Cần xử lý ngay'),
    ('  MEDIUM', severity_counts.get('MEDIUM', 0), 'Cần kiểm tra'),
    ('  LOW', severity_counts.get('LOW', 0), 'Cần theo dõi'),
    ('', '', ''),
    ('Phân bố theo loại lỗi', '', ''),
]
for t, c in type_counts.most_common(20):
    summary_data.append((f'  {t}', c, ''))
    
for i, (label, val, note) in enumerate(summary_data):
    cell = ws0.cell(row=r+i, column=1, value=label)
    if not label.startswith(' '):
        cell.font = Font(bold=True, size=12)
    else:
        cell.font = Font(size=11)
    ws0.cell(row=r+i, column=2, value=val)
    ws0.cell(row=r+i, column=3, value=note)

ws0.column_dimensions['A'].width = 40
ws0.column_dimensions['B'].width = 15
ws0.column_dimensions['C'].width = 30

# ============================================================
# Sheet 1: Tất cả lỗi
# ============================================================
ws1 = wb_out.create_sheet('Tất cả lỗi')

headers = ['ID', 'Loại', 'Severity', 'Order ID', 'Khách hàng', 'Owner', 'Giai đoạn',
           'CRM Giao hàng', 'CRM Thanh toán', 'CRM Ghi DS', 'CRM Duyệt', 'CRM Thực hiện', 'CRM Xuất HĐ', 'CRM Giá trị HĐ',
           'MISA Giao hàng', 'MISA Thực thu', 'MISA Ghi DS', 'MISA Xuất HĐ', 'MISA Giá trị HĐ',
           'Chi tiết', 'Gợi ý xử lý', 'Nhóm cũ', 'Nguồn file']

rows_data = []
for d in discrepancies:
    rows_data.append([
        d['id'], d['type'], d['severity'], d['order_id'], d['customer'], d['owner'], d['gioi_doan'],
        d['CRM_delivery'], d['CRM_payment'], d['CRM_accounting'], d['CRM_approval'], d['CRM_execution'], d['CRM_invoiced'], d['CRM_invoice_value'],
        d['MISA_delivery'], d['MISA_thuc_thu'], d['MISA_accounting'], d['MISA_invoiced'], d['MISA_invoice_value'],
        d['detail'], d['suggestion'], d['old_group'], d['source_files'],
    ])

col_widths = [6, 24, 8, 16, 25, 20, 10, 14, 14, 18, 14, 14, 14, 14, 14, 14, 18, 14, 14, 50, 45, 10, 20]
write_sheet(ws1, 'Tất cả lỗi', headers, rows_data, col_widths)

# Color rows by severity
for r_idx, d in enumerate(discrepancies, 2):
    fill = None
    if d['severity'] == 'HIGH':
        fill = red_fill
    elif d['severity'] == 'MEDIUM':
        fill = yellow_fill
    elif d['severity'] == 'LOW':
        fill = green_fill
    if fill:
        for c in range(1, len(headers)+1):
            ws1.cell(row=r_idx, column=c).fill = fill

# ============================================================
# Sheet 2: CRM-MISA Delivery Mismatch
# ============================================================
ws2 = wb_out.create_sheet('1-Giao hàng lệch')
delivery_discs = [d for d in discrepancies if d['type'] in ('B-Delivery_Mismatch', 'B2-Delivery_Mismatch')]
delivery_rows = [[d['order_id'], d['customer'], d['owner'], d['severity'],
                  d['CRM_delivery'], d['MISA_delivery'], d['MISA_delivery_date'],
                  d['detail'], d['suggestion'], d['old_group']] for d in delivery_discs]
write_sheet(ws2, '1-Giao hàng lệch', 
    ['Order ID', 'Khách hàng', 'Owner', 'Severity', 'CRM Giao hàng', 'MISA Giao hàng', 'MISA Ngày giao',
     'Chi tiết', 'Gợi ý', 'Nhóm cũ'],
    delivery_rows,
    [16, 25, 20, 8, 14, 14, 14, 50, 45, 10])
for r_idx, d in enumerate(delivery_discs, 2):
    fill = red_fill if d['severity'] == 'HIGH' else yellow_fill
    for c in range(1, 11):
        ws2.cell(row=r_idx, column=c).fill = fill

# ============================================================
# Sheet 3: Payment Mismatch
# ============================================================
ws3 = wb_out.create_sheet('2-Thanh toán lệch')
pay_discs = [d for d in discrepancies if d['type'] in ('C-Payment_Mismatch', 'C2-Payment_Mismatch')]
pay_rows = [[d['order_id'], d['customer'], d['owner'], d['severity'],
             d['CRM_payment'], d['MISA_thuc_thu'],
             d['detail'], d['suggestion'], d['old_group']] for d in pay_discs]
write_sheet(ws3, '2-Thanh toán lệch',
    ['Order ID', 'Khách hàng', 'Owner', 'Severity', 'CRM Thanh toán', 'MISA Thực thu',
     'Chi tiết', 'Gợi ý', 'Nhóm cũ'],
    pay_rows,
    [16, 25, 20, 8, 14, 14, 50, 45, 10])

# ============================================================
# Sheet 4: Accounting Record Mismatch
# ============================================================
ws4 = wb_out.create_sheet('3-Ghi DS lệch')
acct_discs = [d for d in discrepancies if d['type'].startswith('D-')]
acct_rows = [[d['order_id'], d['customer'], d['owner'], d['severity'],
              d['CRM_accounting'], d['MISA_accounting'],
              d['detail'], d['suggestion'], d['old_group']] for d in acct_discs]
write_sheet(ws4, '3-Ghi DS lệch',
    ['Order ID', 'Khách hàng', 'Owner', 'Severity', 'CRM Ghi DS', 'MISA Ghi DS',
     'Chi tiết', 'Gợi ý', 'Nhóm cũ'],
    acct_rows,
    [16, 25, 20, 8, 18, 18, 50, 45, 10])

# ============================================================
# Sheet 5: Invoice Mismatch
# ============================================================
ws5 = wb_out.create_sheet('4-Xuất HĐ lệch')
inv_discs = [d for d in discrepancies if d['type'] in ('E-Invoice_Mismatch', 'E2-Invoice_Mismatch', 'M-Invoice_Value_Mismatch')]
inv_rows = [[d['order_id'], d['customer'], d['owner'], d['severity'],
             d['CRM_invoiced'], d['CRM_invoice_value'],
             d['MISA_invoiced'], d['MISA_invoice_value'],
             d['detail'], d['suggestion']] for d in inv_discs]
write_sheet(ws5, '4-Xuất HĐ lệch',
    ['Order ID', 'Khách hàng', 'Owner', 'Severity', 'CRM Xuất HĐ', 'CRM Giá trị',
     'MISA Xuất HĐ', 'MISA Giá trị', 'Chi tiết', 'Gợi ý'],
    inv_rows,
    [16, 25, 20, 8, 14, 16, 16, 16, 55, 45])

# ============================================================
# Sheet 6: Rejected orders excluded
# ============================================================
ws6 = wb_out.create_sheet('5-Từ chối bỏ qua')
write_sheet(ws6, '5-Từ chối bỏ qua',
    ['Ghi chú'],
    [['Đã loại khỏi báo cáo theo yêu cầu: đơn Từ chối ghi không phải issue active cần follow.']],
    [90])

# ============================================================
# Sheet 7: Pre-order Issues
# ============================================================
ws7 = wb_out.create_sheet('6-Pre-order cần XL')
pre_discs = [d for d in discrepancies if d['type'] == 'H-Preorder_Action']
pre_rows = [[d['order_id'], d['customer'], d['detail'], d['MISA_delivery'], d['suggestion']] for d in pre_discs]

# Also add pre-order lines detail
pre_detail_rows = []
for oid, info in sorted(pre_orders.items()):
    if info.get('needs_action'):
        for note in sorted(info['note_actions']):
            if note not in ('Pre order', 'Đã ghi nhận ở revenue', ''):
                crm_cust = crm_orders.get(oid, {}).get('Khách hàng', '')
                pre_detail_rows.append([oid, crm_cust, info['hangiao'], note, f'{info["total_rev"]:,.0f}'])

# Combine: first the discrepancy-level, then detailed lines
all_pre_rows = pre_rows + [['', '', '=== CHI TIẾT ===', '', '']] + pre_detail_rows

write_sheet(ws7, '6-Pre-order cần XL',
    ['Order ID', 'Khách hàng', 'Hạn giao', 'Note', 'Giá trị'],
    [[r[0], r[1], r[2], r[3], r[4]] if len(r) >= 5 else r for r in all_pre_rows],
    [16, 25, 14, 60, 16])

# ============================================================
# Sheet 8: Old Master Unresolved
# ============================================================
ws8 = wb_out.create_sheet('7-Audit cũ còn dấu hiệu')
old_discs = [d for d in discrepancies if d['type'].startswith('K-')]
old_rows = [[d['order_id'], d['old_group'], d['severity'], d['CRM_delivery'], d['CRM_payment'],
             d['CRM_accounting'], d['CRM_execution'],
             d['detail'], d['suggestion']] for d in old_discs]
write_sheet(ws8, '7-Audit cũ còn dấu hiệu',
    ['Order ID', 'Nhóm cũ', 'Severity', 'CRM Giao hàng', 'CRM Thanh toán', 'CRM Ghi DS', 'CRM Thực hiện',
     'Chi tiết', 'Gợi ý'],
    old_rows,
    [16, 10, 8, 14, 14, 18, 14, 55, 45])

# ============================================================
# Sheet 9: Overdue
# ============================================================
ws9 = wb_out.create_sheet('8-Quá hạn giao')
overdue_discs = [d for d in discrepancies if d['type'] == 'G-Overdue']
overdue_rows = [[d['order_id'], d['customer'], d['owner'], d['CRM_delivery'], d['detail'], d['suggestion']] for d in overdue_discs]
write_sheet(ws9, '8-Quá hạn giao',
    ['Order ID', 'Khách hàng', 'Owner', 'CRM Giao hàng', 'Chi tiết', 'Gợi ý'],
    overdue_rows,
    [16, 25, 20, 14, 55, 45])

# ============================================================
# Sheet 10: Missing from MISA
# ============================================================
ws10 = wb_out.create_sheet('9-Không có trên MISA')
missing_misa = [d for d in discrepancies if d['type'] == 'A-Missing_MISA']
mm_rows = [[d['order_id'], d['customer'], d['owner'], d['gioi_doan'], d['CRM_delivery'],
            d['CRM_payment'], d['CRM_accounting'], d['detail'], d['suggestion']] for d in missing_misa]
write_sheet(ws10, '9-Không có trên MISA',
    ['Order ID', 'Khách hàng', 'Owner', 'Giai đoạn', 'CRM Giao hàng', 'CRM Thanh toán', 'CRM Ghi DS',
     'Chi tiết', 'Gợi ý'],
    mm_rows,
    [16, 25, 20, 10, 14, 14, 18, 50, 45])

# ============================================================
# Sheet 11: NVGH Activity
# ============================================================
ws11 = wb_out.create_sheet('10-NVGH cần kiểm tra')
nvgh_discs = [d for d in discrepancies if d['type'] == 'I-NVGH_Activity_Open_Delivery']
nvgh_rows = [[d['order_id'], d['customer'], d['owner'], d['CRM_delivery'],
              'Có NVGH (Xác nhận giao hàng)', d['suggestion']] for d in nvgh_discs]
write_sheet(ws11, '10-NVGH cần kiểm tra',
    ['Order ID', 'Khách hàng', 'Owner', 'CRM Giao hàng', 'NVGH Activity', 'Gợi ý'],
    nvgh_rows,
    [16, 25, 20, 14, 25, 45])

# ============================================================
# Sheet 12: Draft excluded
# ============================================================
ws12 = wb_out.create_sheet('11-Đơn nháp bỏ qua')
write_sheet(ws12, '11-Đơn nháp bỏ qua',
    ['Ghi chú'],
    [['Đã loại khỏi báo cáo theo yêu cầu: chỉ xét đơn Đề nghị ghi hoặc Đã duyệt, không xét đơn nháp.']],
    [90])

# ============================================================
# Sheet 13: No Activity
# ============================================================
ws13 = wb_out.create_sheet('12-Không activity')
noact_discs = [d for d in discrepancies if d['type'] == 'N-No_Activity']
noact_rows = [[d['order_id'], d['customer'], d['owner'], d['detail'], d['suggestion']] for d in noact_discs]
write_sheet(ws13, '12-Không activity',
    ['Order ID', 'Khách hàng', 'Owner', 'Chi tiết', 'Gợi ý'],
    noact_rows,
    [16, 25, 20, 55, 45])

# ============================================================
# Sheet 14: MISA-only (missing in CRM)
# ============================================================
ws14 = wb_out.create_sheet('13-MISA có CRM không')
misa_only = [d for d in discrepancies if d['type'] == 'A2-Missing_CRM']
mo_rows = [[d['order_id'], d['MISA_delivery'], d['MISA_accounting'], d['MISA_invoiced'],
            d['detail'], d['suggestion']] for d in misa_only]
write_sheet(ws14, '13-MISA có CRM không',
    ['Order ID', 'MISA Giao hàng', 'MISA Ghi DS', 'MISA Xuất HĐ', 'Chi tiết', 'Gợi ý'],
    mo_rows,
    [16, 14, 18, 14, 50, 45])

# ============================================================
# Sheet 15: New orders not in master
# ============================================================
ws15 = wb_out.create_sheet('14-Đơn mới chưa phân loại')
# Orders in new data that are NOT in the old master audit
all_data_orders = set(crm_orders.keys()) | set(misa_orders.keys()) | set(so_orders.keys())
new_orders = all_data_orders - set(master_orders.keys())
# Limit to orders with discrepancies
new_with_issues = [d for d in discrepancies if d['order_id'] in new_orders]
new_rows = [[d['order_id'], d['type'], d['severity'], d['CRM_delivery'], d['CRM_payment'],
             d['CRM_accounting'], d['detail']] for d in new_with_issues]
write_sheet(ws15, '14-Đơn mới chưa phân loại',
    ['Order ID', 'Loại lỗi', 'Severity', 'CRM Giao hàng', 'CRM Thanh toán', 'CRM Ghi DS', 'Chi tiết'],
    new_rows,
    [16, 18, 8, 14, 14, 18, 50])

# ============================================================
# Save
# ============================================================
output_path = ROOT / f'bao_cao_doi_soat_CRM_MISA_{TODAY}.xlsx'
wb_out.save(output_path)
print(f"\n✅ Report saved to: {output_path}", file=sys.stderr)
print(f"   Total discrepancies: {len(discrepancies)}", file=sys.stderr)
print(f"   Sheets: {len(wb_out.sheetnames)}", file=sys.stderr)
