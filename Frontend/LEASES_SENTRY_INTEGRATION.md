# Leases Page - Comprehensive Sentry Integration

## Overview

Complete Sentry integration across the entire Leases feature following industry best practices for error tracking, performance monitoring, and structured logging.

---

## 🎯 Integration Coverage

### **1. Error Tracking**

#### **Page-Level Error Boundary**

- **Component:** `Leases.tsx` (root)
- **Coverage:** Catches all React rendering errors
- **Features:**
  - Custom fallback UI with "Try Again" and "Reload Page" options
  - Contextual tags: `component: LeasesPage`, `feature: leases`, `errorBoundary: true`
  - Structured logging with error message, stack trace, and component stack
  - User action tracking (reset vs reload)

#### **CRUD Operation Errors**

All mutation operations capture exceptions with context:

1. **Delete Lease**
   - Tags: `action: delete_lease`, `operation: delete`
   - Context: `leaseId`
   - Logs: info, error levels

2. **Create Lease**
   - Tags: `action: create_lease`
   - Context: lease data
   - Automatic invalidation tracking

3. **Update Lease**
   - Tags: `action: update_lease`
   - Context: `leaseId`, changed fields
   - Optimistic update rollback tracking

4. **Update Status**
   - Tags: `action: update_lease_status`
   - Context: `leaseId`, `current_status`, `new_status`
   - Status transition tracking

5. **Upload Document**
   - Tags: `action: upload_lease_document`
   - Context: `leaseId`, `documentType`, `fileName`, `fileSize`
   - Upload failure tracking

6. **Preview Document**
   - Tags: `action: preview_document`, `operation: preview_document`
   - Context: `leaseId`, `documentId`, `documentType`, `propertyId`, `tenantId`
   - Validation error tracking
   - Secure URL generation failures

---

### **2. Performance Monitoring**

#### **UI Interactions**

Custom spans track critical user flows:

1. **Edit Lease Button** (`ui.click`)
   - Attributes: `leaseId`, `leaseStatus`

2. **Delete Lease** (`lease.delete`)
   - Attributes: `leaseId`
   - Tracks entire deletion flow from click to completion

3. **Change Status Button** (`ui.click`)
   - Attributes: `leaseId`, `currentStatus`

4. **Upload Document Button** (`ui.click`)
   - Attributes: `leaseId`, `hasDocuments`

5. **Document Preview** (`lease.document.preview`)
   - Attributes: `leaseId`, `documentId`, `documentType`, `urlExpiresIn`
   - Tracks secure URL generation performance

6. **Status Filter** (`ui.filter`)
   - Attributes: `filterValue`, `previousFilter`
   - Tracks filter changes and query performance

7. **New Lease Button** (`ui.click`)
   - Attributes: `totalLeases`

#### **Component Rendering**

1. **Leases Table Render** (`ui.render`)
   - Attributes: `leaseCount`, `hasDocuments`
   - Tracks rendering performance with large datasets

---

### **3. Structured Logging**

#### **Trace Level** (Development/Debug)

- Modal open/close events
- Dropdown toggle events
- Filter selection changes
- Page load success

#### **Debug Level** (Verbose Operations)

- Document dropdown interactions
- Document selection for preview
- Status filter changes
- New lease modal opening
- User cancelled actions (e.g., delete confirmation)

#### **Info Level** (Important Operations)

- Lease deletion success
- Secure URL generation success
- User interactions after errors (retry, reload, reset)

#### **Error Level** (Failures)

- Lease deletion failures
- Document preview failures
- Secure URL generation failures
- Page load failures
- Error boundary triggers

---

## 📊 Monitoring Dashboards

### **Recommended Sentry Queries**

#### **Error Rate by Operation**

```text
tags.feature:leases AND tags.action:*
Group by: tags.action
```

#### **Document Preview Performance**

```text
transaction.op:lease.document.preview
Aggregate: p95(transaction.duration)
```

#### **User Flow Success Rate**

```text
tags.component:LeasesPage
Calculate: success_rate by tags.action
```

#### **Optimistic Update Failures**

```text
message:"*rollback*" OR tags.optimistic_failure:true
```

---

## 🔍 Key Metrics Tracked

### **Performance**

- ✅ Delete operation latency
- ✅ Document preview URL generation time
- ✅ Table render time with varying lease counts
- ✅ Filter change response time
- ✅ Modal open/close latency

### **User Behavior**

- ✅ Most common status changes
- ✅ Document upload patterns
- ✅ Filter usage frequency
- ✅ Error recovery actions (retry vs reload)

### **Error Patterns**

- ✅ Preview failures by document type
- ✅ Delete failures by lease status
- ✅ Network vs validation errors
- ✅ Component crash frequency

---

## 🎨 Components Instrumented

| Component | Error Tracking | Performance | Logging |
|-----------|---------------|-------------|---------|
| **Leases.tsx** | ✅ Error Boundary | ✅ All Actions | ✅ Full |
| **LeasesTable.tsx** | ✅ Boundary Ready | ✅ Render Tracking | ✅ Trace |
| **LeaseRow.tsx** | ✅ Inherited | ✅ Inherited | ✅ Inherited |
| **LeaseActions.tsx** | ✅ Component Level | ✅ Click Events | ✅ Debug |
| **LeaseFilters.tsx** | ✅ Inherited | ✅ Filter Changes | ✅ Debug |
| **DocumentDropdown.tsx** | ✅ Component Level | ✅ Toggle/Select | ✅ Trace/Debug |
| **UpdateLeaseStatusModal** | ✅ Full Coverage | ✅ Status Changes | ✅ Full |
| **UploadLeaseDocumentModal** | ✅ Full Coverage | ✅ Uploads | ✅ Full |

---

## 🚀 Benefits

### **For Users**

- Faster issue resolution (detailed error context)
- Better error messages (contextual information)
- Proactive bug fixes before users report

### **For Developers**

- Detailed error reproduction steps
- Performance bottleneck identification
- User flow analysis
- A/B test capability via tags

### **For Product**

- Feature usage analytics
- Error impact assessment
- Performance regression detection
- User experience insights

---

## 📈 Expected Sentry Data

### **Sample Error**

```json
{
  "exception": "Failed to generate secure preview URL",
  "tags": {
    "component": "Leases",
    "action": "preview_document",
    "feature": "leases",
    "operation": "preview_document"
  },
  "contexts": {
    "lease": {
      "leaseId": 123,
      "propertyId": 45,
      "tenantId": 67
    },
    "document": {
      "documentId": 89,
      "documentType": "contract",
      "documentName": "lease_agreement.pdf"
    }
  }
}
```

### **Sample Performance Span**

```json
{
  "op": "lease.delete",
  "description": "Delete Lease",
  "attributes": {
    "leaseId": 123
  },
  "duration": 234.5
}
```

### **Sample Structured Log**

```json
{
  "level": "info",
  "message": "Lease deleted successfully",
  "extra": {
    "leaseId": 123
  }
}
```

---

## ✅ Integration Complete

All components now have:

- ✅ Error boundaries with fallback UI
- ✅ Exception capture with context
- ✅ Performance span tracking
- ✅ Structured logging at appropriate levels
- ✅ User action tracking
- ✅ Component-specific tags

**Result:** Production-ready monitoring with comprehensive visibility into the Leases feature.
