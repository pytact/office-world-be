# API Specification Validation Report: F-008 — Task Management

## Validation Date
2024-01-20

## Summary
Comprehensive validation of `F8_api_spec.md` against:
- `F8_domain_model.md`
- `F8_feature_brief.md`
- `F8_ui_data_contract.md`
- `api_instructions.md`

---

## ✅ PASSED Validations

### 1. Naming Consistency
- ✅ All field names use snake_case consistently (`task_id`, `owner_id`, `company_id`, `project_id`, `employee_id`, `created_at`, `updated_at`)
- ✅ Path parameters use snake_case (`{task_id}`)
- ✅ Query parameters use snake_case (`page_size`, `sort_by`, `sort_order`)
- ✅ JSON fields use snake_case throughout
- ✅ Status enum values match domain model: TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED
- ✅ Permission enum values match domain model: VIEWER, EDITOR

### 2. Endpoints Coverage
- ✅ All 7 endpoints from UI data contract are present:
  - GET `/api/v1/company/tasks` ✅
  - POST `/api/v1/company/tasks` ✅
  - GET `/api/v1/company/tasks/{task_id}` ✅
  - PATCH `/api/v1/company/tasks/{task_id}` ✅
  - PATCH `/api/v1/company/tasks/{task_id}/status` ✅
  - PATCH `/api/v1/company/tasks/{task_id}/assignments` ✅
  - DELETE `/api/v1/company/tasks/{task_id}` ✅

### 3. Required Fields in Responses

#### SCR_TASK_LIST Response
- ✅ Task: `id` (as `task_id`), `name`, `status`, `project_id`, `owner_id`
- ✅ TaskAssignment: `employee_id`, `permission` (included in assignments array)
- ✅ Project: `id`, `name` (included as nested object)
- ✅ Derived fields: `is_owner`, `user_permission`, `can_edit_task`, `can_change_status`

#### SCR_TASK_DETAIL Response
- ✅ Task: `id`, `name`, `description`, `status`, `project_id`, `owner_id`
- ✅ TaskAssignment: `employee_id`, `permission` (included in assignments array)
- ✅ Project: `id`, `name`, `status` (included as nested object)
- ✅ Derived fields: `is_owner`, `user_permission`, `can_edit_task`, `can_change_status`, `can_manage_assignments`, `is_task_read_only`

### 4. Query Parameters
- ✅ All query parameters from UI contract are present:
  - `status` ✅
  - `project_id` ✅
  - `search` ✅
  - `page` ✅
  - `page_size` ✅
  - `sort_by` ✅
  - `sort_order` ✅

### 5. Pagination Structure
- ✅ Uses standard pagination format with navigation URLs (Rule 5)
- ✅ Includes: `items`, `total`, `page`, `page_size`, `total_pages`, `next_page`, `prev_page`
- ✅ Navigation URLs preserve all query parameters

### 6. API Instructions Compliance
- ✅ Rule 1: No `success` field in responses
- ✅ Rule 1a: `X-Request-ID` header in all responses
- ✅ Rule 2: snake_case for all parameters and fields
- ✅ Rule 3: Field validation documented (name: 1-255 chars, description: max 5000 chars)
- ✅ Rule 4: JSON field order not required (noted)
- ✅ Rule 5: Pagination with navigation URLs
- ✅ Rule 6: PATCH for updates, POST for create
- ✅ Rule 8: ETags and conditional requests (If-Match, If-None-Match)
- ✅ Rule 9: Query schema classes with `Depends()` pattern
- ✅ Rule 10: Documentation class structure (`TaskApiDocs`)

### 7. Domain Model Compliance
- ✅ Task entity fields match: Company, Owner, Name, Description, Status, Project, IsDeleted
- ✅ TaskAssignment entity fields match: Task, Employee, Permission
- ✅ Status enum matches: TODO, IN_PROGRESS, HALT, REVIEW, DONE, CANCELLED
- ✅ Permission enum matches: VIEWER, EDITOR
- ✅ Owner is immutable (set at creation, cannot be changed)
- ✅ Hard deletion (IsDeleted marker)

### 8. Business Rules
- ✅ Initial status must be TODO
- ✅ Owner can move task to any status at any time
- ✅ DONE and CANCELLED are terminal states
- ✅ VIEWER: Can view task only
- ✅ EDITOR: Can edit name and description only
- ✅ Editors cannot: Add/remove assignees, change status, remove themselves
- ✅ Project must be ACTIVE to link tasks

---

## ⚠️ ISSUES FOUND

### Issue 1: RBAC Violation - CEO/Manager Delete Permission
**Severity:** HIGH  
**Location:** Section 4.3.7 (DELETE endpoint), Section 3.1 (Role Definitions)

**Problem:**
- Feature Brief (Section 10) states: "CEO and Manager can create, edit, and delete tasks"
- API Spec Section 3.1 states: CEO/Manager "Can delete all company tasks"
- BUT Section 4.3.7 DELETE endpoint says: "Authorization / Roles: Owner only"

**Expected:**
CEO and Manager should be able to delete ANY company task, not just tasks they own.

**Current:**
```markdown
- **Authorization / Roles:** Owner only
```

**Should be:**
```markdown
- **Authorization / Roles:** Owner, CEO, Manager
```

**Impact:**
- Violates feature brief acceptance criteria
- Contradicts role definitions in Section 3.1
- CEO/Manager cannot fulfill their role of managing all company tasks

---

### Issue 2: RBAC Clarification Needed - CEO/Manager Status Change Permission
**Severity:** MEDIUM  
**Location:** Section 4.3.5 (PATCH /status endpoint), Section 3.1

**Problem:**
- Domain Model explicitly states: "Only the task owner can change task status"
- API Spec Section 3.1 says CEO/Manager "Can change status of any company task"
- Section 4.3.5 says: "Authorization / Roles: Owner only"

**Analysis:**
The domain model constraint is explicit: "Only the task owner can change task status". This should take precedence over the role definition.

**Recommendation:**
- Keep status changes as "Owner only" (correct per domain model)
- Update Section 3.1 to clarify: CEO/Manager can change status only for tasks they own (not any task)
- OR if CEO/Manager should be able to change status of any task, update domain model constraint

**Current:**
```markdown
#### CEO (Company Level)
- Can change status of any company task
```

**Should be (if following domain model):**
```markdown
#### CEO (Company Level)
- Can change status of tasks they own (per domain model: only owner can change status)
```

**OR (if CEO/Manager should override):**
Domain model needs to be updated to allow CEO/Manager to change status of any task.

---

### Issue 3: Missing Endpoint - Project List for Task Creation
**Severity:** LOW (Dependency on F-007)  
**Location:** SCR_TASK_CREATE screen requirements

**Problem:**
- UI Data Contract (SCR_TASK_CREATE) requires: "Project (optional selector): id, name, status"
- Only ACTIVE projects should be selectable
- No endpoint in F-008 API spec to fetch projects for selection

**Analysis:**
This is a dependency on F-007 (Project Management). The F-007 API spec has `GET /api/v1/company/projects` which can be filtered by `status=ACTIVE`.

**Recommendation:**
- Add note in F-008 API spec that project selection uses F-007 endpoint: `GET /api/v1/company/projects?status=ACTIVE`
- OR document that frontend should use F-007 API for project selection
- This is acceptable as cross-feature dependency

**Action:**
Add to Section 1.1 or create new section "Cross-Feature Dependencies":
```markdown
### 1.3 Cross-Feature API Usage
- **Project Selection (SCR_TASK_CREATE):** Frontend should use F-007 endpoint `GET /api/v1/company/projects?status=ACTIVE` to populate project selector dropdown.
```

---

### Issue 4: Assignment Update Structure Clarification
**Severity:** LOW  
**Location:** Section 4.3.6 (PATCH /assignments)

**Current Structure:**
```json
{
  "add": [{"employee_id": "...", "permission": "EDITOR"}],
  "remove": [{"employee_id": "..."}]
}
```

**Question:**
The UI data contract doesn't specify the exact structure. The current structure is reasonable, but should verify:
- Can `add` and `remove` be empty arrays?
- Can both be omitted (empty request)?
- Should there be validation that at least one operation is specified?

**Recommendation:**
Add validation note:
```markdown
**Note:** 
- At least one of `add` or `remove` must be provided (cannot be both empty/omitted)
- Empty arrays `[]` are allowed if only one operation is needed
```

---

## 📋 RECOMMENDATIONS

### 1. Resolve CEO/Manager Delete Permission
**Priority:** HIGH  
**Action Required:**
- Update Section 4.3.7 DELETE endpoint authorization to: "Owner, CEO, Manager"
- Update error messages to reflect CEO/Manager can delete
- Verify this aligns with business requirements

### 2. Clarify CEO/Manager Status Change Permission
**Priority:** MEDIUM  
**Action Required:**
- Decide: Should CEO/Manager be able to change status of any task, or only tasks they own?
- If only tasks they own: Update Section 3.1 role definitions
- If any task: Update domain model constraint
- Update Section 4.3.5 accordingly

### 3. Document Cross-Feature Dependencies
**Priority:** LOW  
**Action Required:**
- Add section documenting that project selection uses F-007 API
- Reference F-007 endpoint for project list

### 4. Add Assignment Update Validation
**Priority:** LOW  
**Action Required:**
- Clarify that at least one operation (add or remove) must be provided
- Add validation error for empty request

---

## ✅ VALIDATION CHECKLIST

- [x] Naming consistency (snake_case throughout)
- [x] All endpoints present (7/7)
- [x] Required fields in responses
- [x] Query parameters match UI contract
- [x] Pagination structure correct
- [x] API instructions compliance (all 10 rules)
- [x] Domain model compliance
- [x] Business rules documented
- [ ] **CEO/Manager delete permission** (ISSUE 1)
- [ ] **CEO/Manager status change clarification** (ISSUE 2)
- [ ] Cross-feature dependencies documented (ISSUE 3)
- [ ] Assignment update validation clarified (ISSUE 4)

---

## Conclusion

The API specification is **mostly compliant** with all source documents. The main issues are:

1. **HIGH PRIORITY:** CEO/Manager delete permission contradiction
2. **MEDIUM PRIORITY:** CEO/Manager status change permission clarification needed
3. **LOW PRIORITY:** Cross-feature dependency documentation and assignment validation

All other validations passed successfully. The specification follows API design rules correctly and includes all required fields and endpoints.

---

**Next Steps:**
1. Resolve Issue 1 (CEO/Manager delete permission)
2. Resolve Issue 2 (CEO/Manager status change)
3. Add cross-feature dependency documentation
4. Clarify assignment update validation

