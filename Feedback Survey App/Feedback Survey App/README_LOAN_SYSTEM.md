# Loan Appraiser System

## Overview
This system extends the Feedback application to include a comprehensive loan application and appraisal management system.

## Features Implemented

### For Loan Applicants:
1. **Online Loan Application Submission** (`/loan/apply`)
   - Submit loan applications with complete details
   - Application details: name, email, phone, loan amount, loan type, purpose
   - Employment information: status, employer, monthly income
   - Credit and collateral information
   - Supporting documents list

2. **Application Tracking** (`/loan/my-applications`)
   - View all submitted loan applications
   - Track application status and appraisal progress
   - See approval/rejection decisions with appraiser notes

### For Loan Appraisers:
1. **Centralized Application Queue** (`/appraiser/dashboard`)
   - View all submitted loan applications in a dashboard
   - Filter by status, appraisal status, loan type
   - Search by applicant name or email
   - Statistics overview: total, pending, in-progress, completed

2. **Detailed Application Review** (`/appraiser/application/<id>`)
   - View complete application details
   - See applicant information, employment, income, credit score, collateral
   - Calculate and display LTV (Loan-to-Value) and DTI (Debt-to-Income) ratios

3. **Appraisal Process**
   - Start appraisal with clear action button
   - Add appraisal notes (identity verified, employment verified, income verified, credit reviewed, collateral assessed)
   - Request additional documentation from applicants
   - Approve or reject applications with mandatory comments

4. **Complete Audit Trail**
   - All appraisal activities are logged with timestamps
   - Track who performed each action
   - View chronological history of all appraisal steps

5. **Status Management**
   - Applications cannot proceed to approval without appraisal completion
   - Flag applications as valid/invalid with required reasoning
   - Request additional documents without outright rejection

## Database Schema

### Users Table
- Extended with `role` field (applicant/appraiser)

### Loan Applications Table
- `id`, `user_id`, `applicant_name`, `email`, `phone`
- `loan_amount`, `loan_type`, `employment_status`, `employer_name`
- `monthly_income`, `credit_score`, `collateral_type`, `collateral_value`
- `purpose`, `documents`
- `status` (pending/approved/rejected)
- `appraisal_status` (not_started/in_progress/completed)
- `appraiser_id`, `appraiser_notes`, `validity_flag`
- `ltv_ratio`, `dti_ratio`
- `submitted_at`, `appraisal_started_at`, `appraisal_completed_at`

### Appraisal Activities Table
- Complete audit trail of all appraisal actions
- `loan_application_id`, `appraiser_id`, `activity_type`, `description`
- `performed_at` timestamp

### Document Requests Table
- Track requests for additional documentation
- `loan_application_id`, `appraiser_id`, `document_type`
- `request_message`, `status`, `requested_at`, `responded_at`

## API Endpoints

### Loan Application APIs
- `POST /api/loan/submit` - Submit new loan application
- `GET /api/loan/my-applications` - Get user's applications

### Appraiser APIs
- `GET /api/appraiser/applications` - Get all applications
- `GET /api/appraiser/application/<id>` - Get application details
- `POST /api/appraiser/start-appraisal/<id>` - Start appraisal process
- `POST /api/appraiser/complete-appraisal/<id>` - Complete appraisal with decision
- `POST /api/appraiser/request-documents/<id>` - Request additional documents
- `POST /api/appraiser/add-note/<id>` - Add appraisal note/activity

## Installation & Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python3 App.py
   ```

3. Access the application:
   - Main page: http://localhost:5000
   - Auth: http://localhost:5000/auth
   - Loan application: http://localhost:5000/loan/apply
   - Appraiser dashboard: http://localhost:5000/appraiser/dashboard

## User Roles

### Creating an Appraiser Account:
1. Go to http://localhost:5000/auth
2. Click "Create Account"
3. Fill in details
4. Select "Loan Appraiser" from Account Type dropdown
5. Sign up

### Creating an Applicant Account:
1. Go to http://localhost:5000/auth
2. Click "Create Account"
3. Fill in details
4. Select "Loan Applicant" from Account Type dropdown
5. Sign up

## Acceptance Criteria Coverage

✅ **AC1**: Dedicated interface for appraisers - Appraiser dashboard at `/appraiser/dashboard`

✅ **AC2**: Electronic submission & automatic routing - Applications submitted via `/loan/apply` and visible in appraiser queue

✅ **AC3**: View complete application details - All fields displayed in detail view including applicant info, loan details, documents, timestamps

✅ **AC4**: Initiate appraisal process - "Start Appraisal" button with clear workflow

✅ **AC5**: Review and verify details - Full application review interface with all required information (identity, employment, income, credit, collateral)

✅ **AC6**: Prevent approval without appraisal - Status checks ensure appraisal completion before approval

✅ **AC7**: Flag valid/invalid with mandatory comments - Approve/Reject modals require notes/reasoning

✅ **AC8**: Request additional documentation - Document request functionality without rejecting application

✅ **AC9**: Calculate/verify financial metrics - LTV and DTI ratios automatically calculated and displayed

✅ **AC10**: Complete audit trail - All activities logged with appraiser name, timestamp, and action details

## Testing Workflow

1. Create an appraiser account
2. Create an applicant account
3. Submit a loan application as applicant
4. Login as appraiser
5. View application in dashboard
6. Click "Review" to open detail view
7. Start appraisal
8. Add verification notes
9. Request additional documents (optional)
10. Approve or reject application with notes
11. Verify audit trail shows all actions
12. Login as applicant to see decision

## Financial Metrics Calculation

- **LTV Ratio**: (Loan Amount / Collateral Value) × 100
- **DTI Ratio**: (Monthly Loan Payment / Monthly Income)
  - Monthly Loan Payment approximated as (Loan Amount / 12)

## Security Features

- Role-based access control
- Session management
- Password hashing (SHA-256)
- Login required decorators
- Appraiser-only route protection
