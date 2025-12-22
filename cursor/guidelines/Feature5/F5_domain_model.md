# Project: officeWorld
# Feature: F-005 — Employee Management

## Purpose
Provide a secure, company-bound employee system of record that maintains accurate
personnel data, enforces strict role-based visibility, and preserves historical
information while supporting downstream features such as salary, leave, and
attendance management.

---

# Domain Model: F-005 — Employee Management

## 1. Domain Glossary
| Term | Definition | Examples |
|------|------------|----------|
| Employee | Company-bound personnel record linked to a user | Software Engineer |
| Joining Date | Official employment start date | 2024-04-01 |
| Employment Status | HR-defined employment state | PROBATION |
| Separation Initiated Date | Date resignation is submitted or termination is issued | 2025-02-01 |
| Separation Reason | Reason for resignation or termination | Better opportunity |
| Last Working Day | Final working date after notice | 2025-02-28 |
| Notice Period Days | Number of notice days to be served | 30 |
| Employee Lifecycle | System access lifecycle | Active, Deactivated |
| Soft Deletion | Logical removal while retaining data | Former employee |

---

## 2. Entities and Relationships

### 2.1 Entity List
| Entity | Description |
|--------|-------------|
| Employee | Personnel record representing a user within a company |

---

### 2.2 Entity Details

#### Employee
- **Description**:  
  Represents a company-bound personnel record linked one-to-one with a User.
  Employee is the authoritative source of personal and professional data and
  drives access to HR-related workflows.

- **Key Fields (business-level)**:

  | Field | Description | Notes |
  |------|-------------|-------|
  | User | Linked platform user | Required, one-to-one |
  | Company | Owning company | Required |
  | JoiningDate | Employment start date | Mandatory, immutable |
  | EmploymentStatus | Current HR state | ENUM-controlled |
  | SeparationInitiatedDate | Resignation submission or termination issue date | Required if RESIGNED or TERMINATED |
  | SeparationReason | Reason for resignation or termination | Mandatory if RESIGNED or TERMINATED |
  | LastWorkingDay | Final working day | Valid for resignation & termination |
  | NoticePeriodDays | Notice period duration | 0 allowed for immediate termination |
  | JobTitle | Professional title | Editable by HR/CEO |
  | Department | Functional department | ENUM-controlled |
  | EmploymentType | Nature of employment | ENUM-controlled |
  | EmploymentLevel | Seniority level | ENUM-controlled |
  | WorkEmail | Official email | Company-scoped |
  | Gender | Gender identity | ENUM-controlled |
  | MaritalStatus | Marital status | ENUM-controlled |
  | BloodGroup | Blood group | ENUM-controlled |
  | Nationality | Nationality | Free text |
  | Address | Residential address | Restricted |
  | City | City | API-based dropdown |
  | State | State | Dependent dropdown |
  | Country | Country | API-based dropdown |
  | DocumentType | Identity document type | ENUM-controlled |
  | DocumentNumber | Identity document reference | Restricted |
  | IsActive | System access state | Controls login |
  | IsDeleted | Soft delete flag | CEO-only visibility |

- **ENUM Definitions**:
  - **EmploymentStatus**:  
    TRAINEE, PROBATION, CONFIRMED, NOTICE_PERIOD, ACTIVE, ON_HOLD, TERMINATED, RESIGNED
  - **EmploymentType**:  
    FULL_TIME, PART_TIME, CONTRACT, FREELANCE, TEMPORARY
  - **EmploymentLevel**:  
    INTERN, JUNIOR, MID, SENIOR, LEAD, MANAGER
  - **Department**:  
    FRONTEND, BACKEND, FULLSTACK, QA, HR, DEVOPS, UIUX, PRODUCT, MARKETING, DATA, SUPPORT
  - **Gender**:  
    MALE, FEMALE, OTHER
  - **MaritalStatus**:  
    SINGLE, MARRIED, DIVORCED, WIDOWED, SEPARATED
  - **BloodGroup**:  
    A+, A-, B+, B-, AB+, AB-, O+, O-
  - **DocumentType**:  
    AADHAAR, PAN, DL, VOTER_ID, PASSPORT

- **Relationships**:
  - Exactly one Employee ↔ one User
  - Employee belongs to exactly one Company
  - Employee role mirrors User role (access control owned by F-001)

---

### 2.3 Relationship Overview (Text Diagram)
```text
Company 1..* Employee
User 1..1 Employee
