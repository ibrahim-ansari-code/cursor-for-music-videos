# Azure Blob Storage Setup for Property Images

## Overview

The property images feature uses Azure Blob Storage with SAS tokens for secure, direct browser uploads. The storage account `briklicorestorage` is already configured in the `.env` file.

## Current Configuration

### Storage Account Details

- **Account Name**: `briklicorestorage`
- **Public URL**: `https://briklicorestorage.blob.core.windows.net/`
- **Connection String**: Already in Backend/.env as `AZURE_STORAGE_CONNECTION_STRING`

### Container Required

- **Container Name**: `property-images`
- **Access Level**: Private (we use SAS tokens for access)

## Azure Portal Setup Steps

### 1. Create Container (if not exists)

1. Go to [Azure Portal](https://portal.azure.com)
1. Navigate to Storage Accounts → `briklicorestorage`
1. Click on "Containers" in the left menu
1. Click "+ Container" to create a new container
1. Set:
   - **Name**: `property-images`
   - **Public access level**: Private (no anonymous access)
1. Click "Create"

### 2. Configure CORS (CRITICAL for browser uploads)

This is essential for the frontend to upload directly to Azure Blob Storage.

1. In the storage account, go to "Resource sharing (CORS)" under Settings
1. Select the "Blob service" tab
1. Add a CORS rule with these settings:

```text
Allowed origins: http://localhost:5173, http://localhost:4173, https://your-production-domain.com
Allowed methods: GET, PUT, POST, DELETE, OPTIONS
Allowed headers: *
Exposed headers: *
Max age: 3600
```

**For development**, you can temporarily use `*` for allowed origins:

```text
Allowed origins: *
```

**For production**, replace with your actual domain:

```text
Allowed origins: https://app.brikli.com
```

1. Click "Save"

### 3. Verify Existing Containers

The following containers should already exist (based on the code):

- `avatars` - User profile pictures
- `lease-uploads` - Lease documents
- `payment-receipts` - Payment receipts
- `expense-receipts` - Expense receipts
- `maintenance-photos` - Maintenance photos
- `property-images` - Property images (NEW - create this one)

## Testing the Setup

### 1. Test SAS Token Generation

```bash
# Test the SAS token endpoint (requires valid auth token)
curl -X POST http://localhost:8000/api/properties/{property_id}/images/sas-token \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "property-uuid-here",
    "filename": "test.jpg",
    "content_type": "image/jpeg"
  }'
```

Expected response:

```json
{
  "blob_name": "user_xxx/property_xxx/uuid.jpg",
  "blob_url": "https://briklicorestorage.blob.core.windows.net/property-images/...",
  "sas_token": "sv=2021-08-06&ss=b&srt=o&sp=w...",
  "upload_url": "full_url_with_sas",
  "public_url": "https://briklicorestorage.blob.core.windows.net/property-images/...",
  "expiry": "2025-01-24T15:00:00",
  "container": "property-images",
  "content_type": "image/jpeg"
}
```

### 2. Test Direct Upload

Use the `upload_url` from the response to upload directly:

```javascript
// In browser console or app
const file = document.querySelector('input[type="file"]').files[0];
const uploadUrl = "URL_FROM_SAS_RESPONSE";

fetch(uploadUrl, {
  method: 'PUT',
  headers: {
    'Content-Type': file.type,
    'x-ms-blob-type': 'BlockBlob'
  },
  body: file
}).then(res => {
  if (res.ok) {
    console.log('Upload successful!');
  }
});
```

## Security Considerations

1. **SAS Token Expiry**: Currently set to 1 hour (`SAS_TOKEN_DURATION_HOURS = 1`)
1. **User Isolation**: Files are stored in user-specific folders (`user_{user_id}/property_{property_id}/`)
1. **Authorization**: All endpoints verify user owns the property before generating tokens
1. **CORS**: Only allow specific origins in production

## Troubleshooting

### Common Issues

1. **CORS Error**: "Access to fetch at 'blob.core.windows.net' from origin 'localhost:5173' has been blocked by CORS policy"
   - **Solution**: Configure CORS in Azure Portal (see step 2 above)

1. **403 Forbidden on Upload**:
   - Check SAS token hasn't expired
   - Verify container exists
   - Check account key in connection string is valid

1. **Connection String Parse Error**:
   - Ensure `AZURE_STORAGE_CONNECTION_STRING` is properly formatted
   - Must contain `AccountName=` and `AccountKey=`

1. **Container Not Found**:
   - Create the `property-images` container in Azure Portal

## Environment Variables

Ensure these are set in `Backend/.env`:

```env
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=briklicorestorage;AccountKey=YOUR_KEY;EndpointSuffix=core.windows.net
AZURE_BLOB_PUBLIC_URL=https://briklicorestorage.blob.core.windows.net/
```

## Next Steps

1. Create the `property-images` container in Azure Portal
1. Configure CORS settings for your development URL
1. Test the upload flow end-to-end
1. Add production domain to CORS when deploying
