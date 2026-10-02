"""Generate the evaluation set: 15 realistic letters from FICTIONAL organisations,
each with ground truth, rendered to PNG (clean scan) and to a degraded 'phone photo'.

Every organisation, person, address, phone number and account number here is invented.
Phone numbers use the reserved 555-01xx range.

    python eval/make_letters.py        # needs google-chrome or chromium on PATH
"""

import json
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

HERE = Path(__file__).parent
OUT = HERE / "letters"
TODAY = "2026-10-03"  # the "today" every eval run pretends it is

TO = "Nadia K. Sorokina<br>418 Linden Court, Apt 3<br>Brookhaven, OR 97321"

CSS = """
body{margin:0;background:#fff;font:15px/1.45 Georgia,'Times New Roman',serif;color:#111}
.page{width:816px;min-height:1056px;padding:56px 64px;box-sizing:border-box;position:relative}
.lh{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:3px solid var(--c,#1b3a5c);padding-bottom:12px;margin-bottom:28px}
.lh .org{font:700 22px Arial,Helvetica,sans-serif;color:var(--c,#1b3a5c)}
.lh .sub{font:12px Arial,sans-serif;color:#555}
.lh .right{text-align:right;font:12px Arial,sans-serif;color:#333}
.addr{margin:0 0 28px;font:14px Arial,sans-serif}
h1{font:700 20px Arial,sans-serif;margin:0 0 14px}
table{border-collapse:collapse;width:100%;font:14px Arial,sans-serif;margin:14px 0}
td,th{border:1px solid #999;padding:6px 8px;text-align:left}
th{background:#eee}
.box{border:2px solid #111;padding:10px 14px;margin:16px 0;font:14px Arial,sans-serif}
.big{font:700 26px Arial,sans-serif}
.red{color:#b00}
.fine{font:10.5px Arial,sans-serif;color:#444;margin-top:28px}
.stub{border-top:2px dashed #555;margin-top:36px;padding-top:12px;font:13px Arial,sans-serif}
.stamp{position:absolute;top:150px;right:70px;transform:rotate(-12deg);border:4px solid #b00;color:#b00;font:900 28px Arial;padding:4px 12px;opacity:.85}
"""


def page(color, org, sub, right, body, stamp=""):
    return f"""<!doctype html><meta charset=utf-8><style>{CSS}</style>
<div class=page style="--c:{color}">
{f'<div class=stamp>{stamp}</div>' if stamp else ''}
<div class=lh><div><div class=org>{org}</div><div class=sub>{sub}</div></div><div class=right>{right}</div></div>
<div class=addr>{TO}</div>
{body}
</div>"""


LETTERS = []


def letter(id, html, truth):
    LETTERS.append({"id": id, "html": html, "truth": truth})


letter("01_water_bill", page("#1b5e7a", "Brookhaven Municipal Water &amp; Sewer", "City of Brookhaven Utilities Division",
    "Account: 40-22871-03<br>Bill date: September 24, 2026<br>Customer service: (541) 555-0142",
    """<h1>Your Water &amp; Sewer Bill</h1>
<table><tr><th>Service period</th><td>Aug 20 – Sep 19, 2026</td></tr>
<tr><th>Previous balance</th><td>$0.00</td></tr>
<tr><th>Water usage (4,200 gal)</th><td>$31.62</td></tr>
<tr><th>Sewer</th><td>$44.80</td></tr><tr><th>Stormwater fee</th><td>$7.75</td></tr>
<tr><th><b>Amount due</b></th><td><b>$84.17</b></td></tr>
<tr><th><b>Due date</b></th><td><b>October 20, 2026</b></td></tr></table>
<p>Pay online at brookhavenwater.example, by phone, or mail the stub below. A late fee of $10.00 applies to balances unpaid after the due date.</p>
<div class=stub>Return this portion with payment · Account 40-22871-03 · Amount due $84.17 · Due 10/20/2026</div>"""),
    {"verdict": ["action_needed"], "deadlines": ["2026-10-20"], "amount": 84.17, "direction": "you_owe", "scam": False})

letter("02_shutoff", page("#1b5e7a", "Brookhaven Municipal Water &amp; Sewer", "City of Brookhaven Utilities Division",
    "Account: 40-22871-03<br>Notice date: September 30, 2026<br>Customer service: (541) 555-0142",
    """<h1 class=red>FINAL NOTICE — SERVICE DISCONNECTION</h1>
<p>Our records show your account is past due. To avoid interruption of water service, the past-due balance must be paid in full.</p>
<div class=box>Past-due balance: <span class=big>$212.40</span><br>
Water service will be shut off on or after: <b>October 8, 2026</b></div>
<p>If you cannot pay in full, call Customer Service at (541) 555-0142 before the shut-off date to set up a payment arrangement. Reconnection after shut-off requires a $45.00 fee.</p>
<p>If you have already paid, please disregard this notice.</p>""", stamp="PAST DUE"),
    {"verdict": ["urgent"], "deadlines": ["2026-10-08"], "amount": 212.40, "direction": "you_owe", "scam": False})

letter("03_eob", page("#2e5d34", "Cascade Valley Health Plan", "Member Services · PO Box 5510, Salem, OR",
    "Member ID: CVH-882014<br>Statement date: September 18, 2026<br>Member services: 1-800-555-0177",
    """<h1>Explanation of Benefits</h1>
<p class=big>THIS IS NOT A BILL</p>
<table><tr><th>Date of service</th><th>Provider</th><th>Billed</th><th>Plan paid</th><th>You may owe</th></tr>
<tr><td>08/28/2026</td><td>Riverside Family Clinic</td><td>$310.00</td><td>$275.00</td><td>$35.00</td></tr></table>
<p>The amount you may owe is your copay. Your provider may send you a separate bill. Keep this statement for your records.</p>
<p class=fine>If you disagree with this decision you may file an appeal within 180 days of the date of this notice.</p>"""),
    {"verdict": ["file_it"], "deadlines": [], "amount": None, "direction": None, "scam": False})

letter("04_clinic_bill", page("#6a2c70", "Riverside Family Clinic", "Patient Billing Office",
    "Statement date: September 26, 2026<br>Patient account: RFC-55102<br>Billing questions: (541) 555-0163",
    """<h1>Patient Statement</h1>
<table><tr><th>Date</th><th>Description</th><th>Charges</th><th>Insurance paid</th><th>Balance</th></tr>
<tr><td>08/28/2026</td><td>Office visit, established patient</td><td>$310.00</td><td>$275.00</td><td>$35.00</td></tr></table>
<div class=box>Please pay this amount: <span class=big>$35.00</span><br>Payment due by: <b>November 1, 2026</b></div>
<p>We accept payment online at riversideclinic.example/pay, by phone, or at the front desk.</p>"""),
    {"verdict": ["action_needed"], "deadlines": ["2026-11-01"], "amount": 35.00, "direction": "you_owe", "scam": False})

letter("05_jury", page("#333", "Superior Court of Linn Valley County", "Office of the Jury Commissioner",
    "Juror number: 2026-48817<br>Mailed: September 28, 2026<br>Jury line: (541) 555-0120",
    """<h1>SUMMONS FOR JURY SERVICE</h1>
<p>You are hereby summoned to appear for jury service.</p>
<div class=box>Report date: <b>Tuesday, October 27, 2026 at 8:00 AM</b><br>Location: Linn Valley County Courthouse, 300 Fourth Avenue, Room 110</div>
<p>You must complete the online juror questionnaire, or return the enclosed form, by <b>October 12, 2026</b>. If you are over 70 years of age you may request to be excused.</p>
<p>Failure to respond may result in a fine.</p>"""),
    {"verdict": ["urgent", "action_needed"], "deadlines": ["2026-10-12", "2026-10-27"], "amount": None, "direction": None, "scam": False})

letter("06_ssn_scam", page("#0b2a5b", "Federal Benefits Compliance Office", "Division of Identity Enforcement",
    "Case No: FBC-77-31902<br>Date: September 29, 2026<br>Hotline: (202) 555-0199",
    """<h1 class=red>URGENT: SUSPENSION OF YOUR SOCIAL SECURITY NUMBER</h1>
<p>Dear Beneficiary,</p>
<p>Your Social Security number has been suspended due to suspicious activity linked to your identity. A warrant for your arrest will be issued unless the matter is resolved within 48 hours.</p>
<p>To restore your number and avoid legal action, you must pay a settlement fee of $1,500 using Google Play gift cards. Call our officer at (202) 555-0199 and read the card numbers on the back.</p>
<p>Do not tell anyone about this case, including your bank teller, as this is a confidential federal investigation.</p>
<p>Officer D. Harlan, Badge 4471</p>""", stamp="FINAL"),
    {"verdict": ["scam_warning"], "deadlines": [], "amount": None, "direction": None, "scam": True})

letter("07_prize_scam", page("#8a6d00", "International Sweepstakes Clearing House", "Prize Distribution Department",
    "Claim No: ISC-2026-0091<br>Date: September 22, 2026<br>Claims: winnings.desk@gmail.com",
    """<h1>CONGRATULATIONS! YOU HAVE WON $850,000.00</h1>
<p>Your name was selected in our international lottery draw. To release your prize, a one-time processing fee of $499.00 is required.</p>
<p>Deposit the fee in cash at any Bitcoin ATM using the wallet code enclosed, then email your receipt to winnings.desk@gmail.com. Prizes not claimed within 10 days are forfeited.</p>
<p>Keep this letter confidential until your funds arrive.</p>"""),
    {"verdict": ["scam_warning"], "deadlines": [], "amount": None, "direction": None, "scam": True})

letter("08_warranty_ad", page("#7a0000", "Vehicle Protection Services Center", "Notice Processing Dept.",
    "Ref: VPS-118-2203<br>Date: September 25, 2026<br>Call: 1-888-555-0110",
    """<h1 class=red>FINAL NOTICE — VEHICLE SERVICE CONTRACT</h1>
<p>Our records indicate the factory warranty on your vehicle may have expired or is about to expire. You can still activate extended coverage before your file is closed.</p>
<p>Call 1-888-555-0110 today to activate. Act now — this is your last chance.</p>
<p class=fine>Vehicle Protection Services Center is not affiliated with your vehicle manufacturer or dealer. This is an advertisement for an optional service contract. Not a bill.</p>""", stamp="FINAL NOTICE"),
    {"verdict": ["file_it", "scam_warning"], "deadlines": [], "amount": None, "direction": None, "scam": None})

letter("09_rx_ready", page("#00695c", "Northgate Pharmacy", "Store #214 · 1200 Northgate Blvd",
    "Date: October 1, 2026<br>Pharmacy: (541) 555-0155",
    """<h1>Your prescription is ready</h1>
<p>Your prescription refill for <b>Lisinopril 10 mg</b> is ready for pickup at the pharmacy counter.</p>
<p>Prescriptions not picked up within 10 days are returned to stock. Your copay is $4.00, payable at pickup.</p>
<p>Questions? Call us at (541) 555-0155.</p>"""),
    {"verdict": ["action_needed", "urgent"], "deadlines": ["2026-10-11"], "amount": 4.00, "direction": "you_owe", "scam": False, "deadline_optional": True})

letter("10_property_tax", page("#4a3b00", "Linn Valley County Assessor &amp; Tax Collector", "Property Tax Division",
    "Parcel: 11-04-27-B-0318<br>Statement date: September 15, 2026<br>Tax office: (541) 555-0131",
    """<h1>2026–27 Property Tax Statement — Second Installment</h1>
<table><tr><th>Installment</th><th>Due date</th><th>Amount</th><th>Status</th></tr>
<tr><td>First</td><td>05/15/2026</td><td>$1,842.00</td><td>PAID</td></tr>
<tr><td>Second</td><td>11/15/2026</td><td>$1,842.00</td><td>DUE</td></tr></table>
<p>Pay the second installment by <b>November 15, 2026</b> to avoid interest. Seniors 62 and older may qualify for property tax deferral; applications are due April 15.</p>"""),
    {"verdict": ["action_needed"], "deadlines": ["2026-11-15"], "amount": 1842.00, "direction": "you_owe", "scam": False})

letter("11_plan_change", page("#2e5d34", "Evergreen Senior Health Plan", "Annual Notice of Change for 2027",
    "Member ID: ESH-30018<br>Date: September 26, 2026<br>Member services: 1-800-555-0188",
    """<h1>Important changes to your plan for 2027</h1>
<p>Starting January 1, 2027, your monthly premium will change from $0 to $18.00, and your specialist copay will change from $35 to $40.</p>
<p>If you want to stay in this plan, you don't need to do anything. If you want to compare or change plans, you can do so during Open Enrollment, from <b>October 15 to December 7, 2026</b>.</p>"""),
    {"verdict": ["action_needed", "file_it"], "deadlines": ["2026-12-07"], "amount": None, "direction": None, "scam": False, "deadline_optional": True})

letter("12_refund", page("#1b3a5c", "Oregon Coast Electric Cooperative", "Member Accounts",
    "Account: OCE-90021<br>Date: September 27, 2026<br>Member line: (541) 555-0170",
    """<h1>Capital Credit Refund</h1>
<p>As a member of the cooperative, you are receiving a refund of capital credits for past years of service.</p>
<div class=box>Refund amount: <span class=big>$63.50</span><br>A check is enclosed. No action is required other than depositing it.</div>"""),
    {"verdict": ["file_it", "action_needed"], "deadlines": [], "amount": 63.50, "direction": "you_receive", "scam": False})

letter("13_appointment", page("#6a2c70", "Riverside Family Clinic", "Appointment Desk",
    "Date: September 30, 2026<br>Appointments: (541) 555-0164",
    """<h1>Appointment reminder</h1>
<p>You have an appointment with <b>Dr. Elena Varga</b> for your annual physical.</p>
<div class=box><b>Tuesday, October 6, 2026 at 10:30 AM</b><br>Riverside Family Clinic, 22 Mill Street, Suite 4</div>
<p>Please do not eat or drink anything except water for 8 hours before your visit (fasting blood test). Bring your insurance card and a list of your medicines. To reschedule, call at least 24 hours in advance.</p>"""),
    {"verdict": ["urgent", "action_needed"], "deadlines": ["2026-10-06"], "amount": None, "direction": None, "scam": False})

letter("14_bank_lock_scam", page("#003366", "Security Department — Account Services", "Customer Protection Unit",
    "Notice ID: SEC-55-1092<br>Date: September 30, 2026<br>Verification line: 1-877-555-0193",
    """<h1 class=red>Your account has been locked</h1>
<p>We detected unusual activity on your bank account. Your account has been temporarily locked for your protection.</p>
<p>To unlock it you must call the verification line at 1-877-555-0193 within 24 hours and confirm your full card number, PIN and online banking password. To protect the investigation, do not tell your bank branch staff about this notice.</p>
<p>Our agent may ask you to move your savings to a safe holding account by Zelle while the review is completed.</p>"""),
    {"verdict": ["scam_warning"], "deadlines": [], "amount": None, "direction": None, "scam": True})

letter("15_cd_maturity", page("#003366", "Willamette Community Bank", "Deposit Services · Member FDIC",
    "Account ending 4410<br>Date: September 20, 2026<br>Call: (541) 555-0148",
    """<h1>Your Certificate of Deposit is maturing</h1>
<p>Your 12-month CD ending in 4410 (balance $10,412.88) matures on <b>October 18, 2026</b>.</p>
<p>If you take no action, it will automatically renew for another 12 months at the current rate of 3.10% APY. You have a 10-day grace period after maturity to withdraw or change the term without penalty.</p>
<p>Never share your PIN or password with anyone, including bank employees. We will never ask for it.</p>"""),
    {"verdict": ["file_it", "action_needed"], "deadlines": ["2026-10-18"], "amount": None, "direction": None, "scam": False, "deadline_optional": True})


# ---------------------------------------------------------------- hard set
# Letters designed to break the easy path: look-alike scams with no keyword the
# rules know, a deadline hidden on page 2 or in fine print, a non-English letter,
# and terrible photos.

HARD = []


def hard(id, pages, truth, degrade="normal"):
    HARD.append({"id": id, "pages": pages, "truth": truth, "degrade": degrade})


hard("h01_deed_service", [page("#3b2f2f", "Property Record Retrieval Department", "Homeowner Document Services",
    "Parcel: 11-04-27-B-0318<br>Notice date: September 26, 2026<br>Response requested by: October 15, 2026",
    """<h1>PROPERTY DEED NOTICE — RESPONSE REQUESTED</h1>
<p>Our records show you do not have an official certified copy of your property deed for 418 Linden Court. It is recommended that all homeowners obtain a certified copy.</p>
<div class=box>Document fee: <span class=big>$89.00</span><br>Response requested by: <b>October 15, 2026</b></div>
<p>Return the form below with your payment to receive your certified deed copy and property profile.</p>
<p class=fine>Property Record Retrieval Department is a private company and is not affiliated with any county or government agency. A copy of your deed may be obtained from the County Recorder for a small fee. This is not a bill. This product or service has not been approved or endorsed by any government agency.</p>""")],
    {"verdict": ["scam_warning", "file_it"], "deadlines": [], "amount": None, "direction": None, "scam": True})

hard("h02_page_two", [page("#1b3a5c", "Oregon Coast Electric Cooperative", "Member Accounts",
    "Account: OCE-90021<br>Date: September 28, 2026<br>Member line: (541) 555-0170",
    """<h1>Important information about your account</h1>
<p>Thank you for being a member of Oregon Coast Electric Cooperative. This fall we are upgrading meters in your neighborhood. A technician may visit your property; no appointment is necessary and there is no charge.</p>
<p>We are also updating our billing system. Your account number and member benefits are not changing.</p>
<p>Please see the next page for your current statement.</p>"""),
    page("#1b3a5c", "Oregon Coast Electric Cooperative", "Statement — page 2 of 2", "Account: OCE-90021",
    """<h1>Current statement</h1>
<table><tr><th>Previous balance</th><td>$0.00</td></tr><tr><th>Electric service Aug 25 – Sep 24</th><td>$156.20</td></tr>
<tr><th><b>Total due</b></th><td><b>$156.20</b></td></tr><tr><th><b>Due date</b></th><td><b>10/09/2026</b></td></tr></table>""")],
    {"verdict": ["urgent"], "deadlines": ["2026-10-09"], "amount": 156.20, "direction": "you_owe", "scam": False})

hard("h03_debt_validation", [page("#333", "Summit Recovery Partners, LLC", "Licensed Collection Agency · Portland, OR",
    "Reference: SRP-4418-207<br>Date: September 25, 2026<br>Phone: (503) 555-0126",
    """<h1>Validation Notice</h1>
<p>Summit Recovery Partners is a debt collector. We are trying to collect a debt that you owe to Riverside Family Clinic. We will use any information you give us to help collect the debt.</p>
<table><tr><th>As of August 30, 2026 you owed</th><td>$1,284.55</td></tr><tr><th>Total amount of the debt now</th><td>$1,284.55</td></tr></table>
<div class=box>How can you dispute the debt? Call or write to us by <b>November 9, 2026</b> to dispute all or part of the debt. If you do not, we will assume that our information is correct.</div>
<p>If you write to us by November 9, 2026, we must stop collection on any amount you dispute until we send you information that shows you owe the debt.</p>""")],
    {"verdict": ["action_needed", "urgent"], "deadlines": ["2026-11-09"], "amount": 1284.55, "direction": "you_owe", "scam": False})

hard("h04_fine_print", [page("#2e5d34", "Cascade Valley Health Plan", "Member Services",
    "Member ID: CVH-882014<br>Date: September 21, 2026<br>Member services: 1-800-555-0177",
    """<h1>Thank you for being a valued member!</h1>
<p>We're glad you chose Cascade Valley Health Plan this year. Inside you'll find tips for staying healthy this fall: get your flu shot, walk 20 minutes a day, and ask your doctor about a free wellness visit.</p>
<p>Flu shots are available at no cost at any in-network pharmacy.</p>
<p class=fine>Coverage renewal: because your income verification is incomplete, your coverage will end on October 31, 2026 unless we receive the enclosed Income Verification Form (CV-12) by October 24, 2026. Questions: 1-800-555-0177.</p>""")],
    {"verdict": ["action_needed", "urgent"], "deadlines": ["2026-10-24"], "amount": None, "direction": None, "scam": False})

hard("h05_spanish_school", [page("#7a3e00", "Distrito Escolar de Brookhaven", "Oficina de Transporte",
    "Fecha: 29 de septiembre de 2026<br>Teléfono: (541) 555-0138",
    """<h1>Aviso: formulario de transporte escolar</h1>
<p>Estimado padre, madre o tutor:</p>
<p>Su nieto Mateo está inscrito en la ruta de autobús 14. Para continuar con el servicio de autobús, debe firmar y devolver el formulario de permiso adjunto a más tardar el <b>16 de octubre de 2026</b>.</p>
<p>Si no recibimos el formulario, el estudiante no podrá usar el autobús a partir del 19 de octubre. El servicio es gratuito.</p>""")],
    {"verdict": ["action_needed"], "deadlines": ["2026-10-16"], "amount": None, "direction": None, "scam": False})

hard("h06_tax_relief", [page("#0b2a5b", "National Tax Resolution Center", "Notice of Pending Levy Action",
    "Notice: NTR-26-55871<br>Date: September 27, 2026<br>Resolution line: 1-866-555-0105",
    """<h1 class=red>NOTICE OF STATE TAX LIEN / LEVY</h1>
<p>Public records indicate a tax matter may be associated with your name. Unresolved tax debts can result in wage garnishment, bank levy, or seizure of property.</p>
<p>You may qualify for a reduced settlement. Call our Resolution Line at 1-866-555-0105 today to speak with a tax relief specialist and stop collection activity. Have your Social Security number and bank information ready.</p>
<p class=fine>National Tax Resolution Center is a private tax resolution firm and is not a government agency.</p>""", stamp="FINAL NOTICE")],
    {"verdict": ["scam_warning", "file_it"], "deadlines": [], "amount": None, "direction": None, "scam": True})

hard("h07_benefit_card", [page("#123c69", "Senior Benefits Card Center", "Member Enrollment",
    "Ref: SBC-0091-26<br>Date: September 30, 2026<br>Activation line: 1-855-555-0182",
    """<h1>Your new benefits card has been approved</h1>
<p>Good news! You have been approved for a new prepaid grocery and utility allowance card worth up to $2,400 per year.</p>
<p>To activate your card, call 1-855-555-0182. For verification, please have your Medicare number, date of birth and bank routing number ready. Activation must be completed this month.</p>""")],
    {"verdict": ["scam_warning"], "deadlines": [], "amount": None, "direction": None, "scam": True})

hard("h08_dark_blurry", "01_water_bill",
    {"verdict": ["action_needed"], "deadlines": ["2026-10-20"], "amount": 84.17, "direction": "you_owe", "scam": False},
    degrade="awful")

hard("h09_sideways", "04_clinic_bill",
    {"verdict": ["action_needed"], "deadlines": ["2026-11-01"], "amount": 35.00, "direction": "you_owe", "scam": False},
    degrade="sideways")


# ---------------------------------------------------------------- held-out set
# Written AFTER the rules and prompts were tuned on core+hard, run once, not tuned on.

hard("x01_homestead_service", [page("#2b2b52", "Homestead Exemption Processing Center", "Property Owner Services",
    "File No: HEP-77120<br>Date: September 29, 2026<br>Reply by: October 20, 2026",
    """<h1>HOMESTEAD EXEMPTION — ACTION REQUIRED</h1>
<p>Our review of public property records shows that the residence at 418 Linden Court may be eligible for a homestead exemption that could lower your property taxes.</p>
<p>For a one-time service charge of <b>$149.00</b> we will prepare and submit your exemption application on your behalf. Return the enclosed form with your check by October 20, 2026.</p>
<p class=fine>We are a private document preparation service. You may apply for the exemption yourself directly with the County Assessor at no cost.</p>""")],
    {"verdict": ["scam_warning", "file_it"], "deadlines": [], "amount": None, "direction": None, "scam": True}, )

hard("x02_hoa_violation", [page("#335533", "Linden Court Homeowners Association", "Board of Directors",
    "Date: September 30, 2026<br>Management office: (541) 555-0157",
    """<h1>Notice of Violation — Second Notice</h1>
<p>During the September 28 inspection, trash bins were observed stored in front of the garage at Unit 3, in violation of Section 7.2 of the Rules &amp; Regulations.</p>
<p>Please move the bins out of view by <b>October 14, 2026</b>. If the violation is not corrected, a fine of $50.00 will be assessed to your account.</p>
<p>If you believe this notice is in error, you may request a hearing with the Board by calling the management office.</p>""")],
    {"verdict": ["action_needed", "urgent"], "deadlines": ["2026-10-14"], "amount": None, "direction": None, "scam": False})

hard("x03_rebate_cashapp", [page("#0a5a5a", "Energy Rebate Distribution Office", "Senior Utility Assistance Program",
    "Ref: ERD-5512<br>Date: September 30, 2026<br>Agent: rebates.office@outlook.com",
    """<h1>You qualify for a $650 utility rebate</h1>
<p>Congratulations, your household has been selected for the Senior Utility Assistance rebate of $650.00.</p>
<p>To release the rebate, a refundable verification deposit of $45.00 is required. Send the deposit by Cash App to $RebateDesk and email a screenshot to rebates.office@outlook.com. Unclaimed rebates expire in 72 hours.</p>""")],
    {"verdict": ["scam_warning"], "deadlines": [], "amount": None, "direction": None, "scam": True})

hard("x04_revenue_adjustment", [page("#3d3d3d", "Oregon Department of Revenue", "Personal Income Tax Division",
    "Letter ID: L1408822916<br>Date: September 23, 2026<br>Phone: (503) 555-0114",
    """<h1>Notice of Adjustment to Your 2025 Return</h1>
<p>We adjusted your 2025 Oregon return because the amount of your senior medical deduction did not match our records.</p>
<table><tr><th>Refund you claimed</th><td>$412.00</td></tr><tr><th>Adjusted refund</th><td>$318.00</td></tr></table>
<p>Your adjusted refund of $318.00 will be issued within 4–6 weeks. If you disagree, you must file a written objection within 90 days of the date of this notice. No payment is required.</p>""")],
    {"verdict": ["file_it", "action_needed"], "deadlines": [], "amount": 318.00, "direction": "you_receive", "scam": False})

hard("x05_lab_results", [page("#6a2c70", "Riverside Family Clinic", "Patient Portal Notice",
    "Date: October 1, 2026<br>Nurse line: (541) 555-0166",
    """<h1>Your lab results are available</h1>
<p>Dr. Elena Varga has reviewed your recent blood test. Most results are in the normal range.</p>
<p>Your potassium level was slightly high. Dr. Varga would like you to <b>repeat the blood test within the next 5 days</b> and to avoid potassium supplements and salt substitutes until then. Please call the nurse line to schedule a lab visit.</p>""")],
    {"verdict": ["urgent", "action_needed"], "deadlines": [], "amount": None, "direction": None, "scam": False})

hard("x06_library_ad", [page("#7a3e00", "Brookhaven Public Library Foundation", "Annual Fall Book Sale",
    "Date: September 18, 2026",
    """<h1>You're invited: Fall Book Sale!</h1>
<p>Join us Saturday, October 17, 10 AM – 3 PM, in the library community room. Hardcovers $1, paperbacks 50¢. Members get early access from 9 AM.</p>
<p>All proceeds support children's reading programs. Donations of gently used books are welcome through October 10.</p>""")],
    {"verdict": ["file_it"], "deadlines": [], "amount": None, "direction": None, "scam": False})


def chrome() -> str:
    for c in ("google-chrome", "chromium", "chromium-browser"):
        if shutil.which(c):
            return c
    raise SystemExit("needs google-chrome or chromium")


def render(exe: str, html: Path, png: Path):
    subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1.5",
                    "--window-size=816,1056", f"--screenshot={png}", html.resolve().as_uri()],
                   check=True, capture_output=True)


def phoneify(src: Path, dst: Path, seed: int, degrade: str = "normal"):
    """Make a clean render look like a quick phone snapshot on a kitchen table."""
    rnd = random.Random(seed)
    img = Image.open(src).convert("RGB")
    w, h = img.size
    table = Image.new("RGB", (int(w * 1.18), int(h * 1.14)), (120, 86, 52))
    d = ImageDraw.Draw(table)
    for y in range(0, table.size[1], 9):  # wood grain
        d.line([(0, y), (table.size[0], y + rnd.randint(-6, 6))], fill=(110 + rnd.randint(0, 25), 78, 46), width=2)
    table.paste(img, ((table.size[0] - w) // 2, (table.size[1] - h) // 2))
    img = table.rotate(rnd.uniform(-5, 5), resample=Image.BICUBIC, expand=False, fillcolor=(100, 70, 40))
    # perspective: top edge narrower, like holding the phone at an angle
    W, H = img.size
    k = rnd.uniform(0.02, 0.06) * W
    coeffs = _persp([(k, 0), (W - k, 0), (W, H), (0, H)], [(0, 0), (W, 0), (W, H), (0, H)])
    img = img.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    # uneven lighting: a soft shadow across one corner
    shade = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shade).ellipse([-W * 0.4, H * 0.55, W * 0.7, H * 1.5], fill=rnd.randint(70, 110))
    shade = shade.filter(ImageFilter.GaussianBlur(120))
    img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, shade)
    img = ImageEnhance.Brightness(img).enhance(rnd.uniform(0.85, 1.0))
    img = img.filter(ImageFilter.GaussianBlur(rnd.uniform(0.4, 0.9)))
    if degrade == "awful":  # evening kitchen light, shaky hands
        img = ImageEnhance.Brightness(img).enhance(0.45)
        img = ImageEnhance.Contrast(img).enhance(0.6)
        img = img.filter(ImageFilter.GaussianBlur(2.2))
    if degrade == "sideways":
        img = img.rotate(90, expand=True)
    scale = 0.5 if degrade == "awful" else 0.75
    img = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)))
    img.save(dst, "JPEG", quality=55 if degrade == "awful" else rnd.randint(70, 82))


def _persp(pa, pb):
    import numpy as np
    m = []
    for (x, y), (X, Y) in zip(pa, pb):
        m.append([X, Y, 1, 0, 0, 0, -x * X, -x * Y])
        m.append([0, 0, 0, X, Y, 1, -y * X, -y * Y])
    A = np.array(m, dtype=float)
    B = np.array(pa, dtype=float).reshape(8)
    return np.linalg.solve(A, B).tolist()


def main():
    OUT.mkdir(exist_ok=True)
    exe = chrome()
    truth = {"today": TODAY, "letters": {}}
    for i, L in enumerate(LETTERS):
        html = OUT / f"{L['id']}.html"
        html.write_text(L["html"], encoding="utf8")
        png = OUT / f"{L['id']}.png"
        render(exe, html, png)
        phoneify(png, OUT / f"{L['id']}.photo.jpg", seed=i)
        truth["letters"][L["id"]] = {**L["truth"], "set": "core", "photos": [f"{L['id']}.photo.jpg"]}
        print("rendered", L["id"])
    for i, H in enumerate(HARD):
        if isinstance(H["pages"], str):  # reuse a core letter with a nastier photo
            src_pngs = [OUT / f"{H['pages']}.png"]
        else:
            src_pngs = []
            for n, html_text in enumerate(H["pages"]):
                html = OUT / f"{H['id']}.p{n + 1}.html"
                html.write_text(html_text, encoding="utf8")
                png = OUT / f"{H['id']}.p{n + 1}.png"
                render(exe, html, png)
                src_pngs.append(png)
        photos = []
        for n, png in enumerate(src_pngs):
            dst = OUT / f"{H['id']}.p{n + 1}.photo.jpg"
            phoneify(png, dst, seed=100 + i * 10 + n, degrade=H["degrade"])
            photos.append(dst.name)
        group = "holdout" if H["id"].startswith("x") else "hard"
        truth["letters"][H["id"]] = {**H["truth"], "set": group, "photos": photos}
        print("rendered", H["id"])
    (OUT / "truth.json").write_text(json.dumps(truth, indent=1))


if __name__ == "__main__":
    main()
