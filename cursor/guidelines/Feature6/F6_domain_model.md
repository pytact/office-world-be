create me single domain file
# Project: officeWorld
# Feature: F-006 — Salary Management

## Purpose
Provide a secure, auditable, and time-based salary management system that defines
employee compensation, maintains immutable salary history, manages bank details,
executes salary payments, and delivers downloadable salary slips to employees,
with strict role-based access control.

---

# Domain Model: F-006 — Salary Management

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| Salary Details | Time-bound salary configuration for an employee | ₹80,000/month |
| Salary Payment | Executed salary record for a specific month | March 2025 |
| Salary History | Immutable record of salary configuration changes | Increment log |
| Bank Info | Employee bank account used for salary payments | HDFC Account |
| Salary Slip | Generated document for a salary payment | PDF payslip |
| Effective Period | Date range when a salary configuration applies | Jan–Dec 2025 |

---

## 2. Entities and Relationships

### 2.1 Entity List
| Entity | Description |
|--------|-------------|
| BankInfo | Employee bank account used for salary payments |
| SalaryDetails | Salary configuration with effective dates |
| SalaryPayment | Monthly executed salary record |
| SalaryHistory | Immutable audit log of salary changes |

---

### 2.2 Entity Details

#### BankInfo
- **Description**:  
  Represents an employee’s bank account used for salary payments. Only one active
  bank account exists per employee at any time.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | Employee | Owning employee | Required |
  | BankName | Bank identifier | ENUM-controlled |
  | Branch | Bank branch | Free text |
  | AccountNumber | Bank account number | Sensitive |
  | IFSCCode | Bank routing code | Sensitive |

- **BankName ENUM**:
```text
HDFC
ICICI
SBI
AXIS
KOTAK
PNB
BOB


Rules:

Updates affect future payments only

Past salary records remain unchanged

SalaryDetails

Description:
Defines the monthly gross salary configuration for an employee over a specific
effective period. Only one active configuration is allowed at any time.

Key Fields (business-level):

Field	Description	Notes
Employee	Employee being paid	Required
EffectiveFrom	Start date	Inclusive
EffectiveTo	End date	Auto-set on change
Amount	Monthly gross amount	Currency-based
Currency	Salary currency	ENUM-controlled
PaymentFrequency	Payment cadence	ENUM-controlled

Currency ENUM (with symbols):

INR (₹)
USD ($)
EUR (€)
GBP (£)
AUD (A$)
CAD (C$)


PaymentFrequency ENUM:

MONTHLY
BI_WEEKLY
WEEKLY


Rules:

Only one active SalaryDetails per employee

Updating salary auto-sets EffectiveTo on the previous record

Future salary payments use the latest active configuration

SalaryPayment

Description:
Represents a completed salary payment for a specific employee, month, and year.
Records are immutable and append-only.

Key Fields (business-level):

Field	Description	Notes
Employee	Paid employee	Required
Amount	Paid amount	Derived from SalaryDetails
Month	Salary month	1–12
Year	Salary year	YYYY
PaidOn	Payment date	Execution date
PaymentMethod	Mode of payment	ENUM-controlled
SlipURL	Salary slip location	Downloadable

PaymentMethod ENUM:

BANK_TRANSFER
UPI
CHEQUE
CASH


Rules:

Created only by CEO or HR

Cannot be modified or deleted

SalaryHistory

Description:
Immutable audit record capturing changes to SalaryDetails over time.

Key Fields:

PreviousAmount

NewAmount

EffectiveFrom

ChangedBy

CreatedAt

2.3 Relationship Overview (Text Diagram)
Employee 1..1 BankInfo
Employee 1..* SalaryDetails
Employee 1..* SalaryPayment
SalaryDetails 1..* SalaryHistory

3. Workflows / Use Cases
3.1 Configure or Update Salary

Actor: CEO, HR

Trigger: New hire salary setup or increment

Primary Flow:

Create new SalaryDetails with EffectiveFrom

System auto-sets EffectiveTo on previous SalaryDetails

SalaryHistory entry created

Post-conditions:

Exactly one active SalaryDetails exists

3.2 Update Bank Info

Actor: CEO, HR

Primary Flow:

Update bank account details

Future salary payments use updated bank info

Post-conditions:

Past salary payments remain unchanged

3.3 Execute Salary Payment

Actor: CEO, HR

Trigger: Salary processing for a given month

Primary Flow:

Retrieve active SalaryDetails

Create SalaryPayment for month/year

Generate salary slip

Email salary slip to employee

Post-conditions:

SalaryPayment stored

SalarySlip available for download

3.4 View Salary Information

Access Rules:

CEO / HR: Full access to all salary data

Employee:

View own SalaryDetails

View own SalaryPayment history

Download own salary slips

Receive salary slips via email only

Restrictions:

Employees cannot access others’ salary data

4. Business Rules
Rule ID	Description	Type	Related Entities
BR-601	Salary amount represents monthly gross pay	Constraint	SalaryDetails
BR-602	Only one active SalaryDetails per employee	Constraint	SalaryDetails
BR-603	Salary updates auto-close previous config	Lifecycle	SalaryDetails
BR-604	Salary payments are immutable	Constraint	SalaryPayment
BR-605	Only CEO and HR can create salary payments	Authority	SalaryPayment
BR-606	Bank info updates affect future payments only	Constraint	BankInfo
BR-607	Employees can view only their own salary data	Security	SalaryDetails
BR-608	Salary slip generated per salary payment	Behavior	SalaryPayment
5. Assumptions

No payroll deductions or tax calculations are included

Salary payment execution is manual (not scheduled)

Salary slips are generated via an external service/template

All salary-related actions are audit logged

No retroactive salary recalculation is supported

6. Non-Functional Domain Considerations

Strong encryption for bank and salary data

High auditability and compliance readiness

Strict RBAC enforcement

Data immutability guarantees

Scalable processing for large employee bases