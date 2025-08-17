# Settings Page Redesign - Implementation Plan

## Overview

Rebuild Settings.jsx with modern design matching Dashboard/Properties pages. Focus on clean UI, tab-based navigation, and modular components.

## File Structure

```text
Frontend/src/
├── pages/
│   └── Settings.jsx (main container - replace existing)
└── components/
    └── settings/
        ├── ProfileCard.jsx
        ├── ProfileForm.jsx
        ├── SecurityForm.jsx
        ├── PreferencesForm.jsx
        └── NotificationSettings.jsx
```

## Implementation Steps

### 1. Main Settings Container (pages/Settings.jsx)

```jsx
// Tab-based navigation with responsive grid layout
// Tabs: Profile | Security | Preferences | Notifications
// Grid: 4-col sidebar (ProfileCard) + 8-col content area
```

Key features:

- Tab navigation matching app style
- Responsive grid layout
- Clean white background
- No shadow/card styling (match Dashboard/Properties)

### 2. ProfileCard Component

```jsx
// Left sidebar with user info
- Avatar with modern upload (drag-drop, overlay button)
- User name, email, role
- Member since date
- Account stats
```

Avatar upload improvements:

- Drag & drop zone
- Click to upload fallback
- Image preview before save
- Loading states
- Error handling

### 3. ProfileForm Component

```jsx
// Personal information form
- First/Last name (editable)
- Email (read-only)
- Phone number
- Save only when changes made
- Inline validation
```

### 4. SecurityForm Component

```jsx
// Password management
- New password field
- Confirm password field
- Password strength indicator
- Requirements checklist
- Clear success/error states
```

### 5. PreferencesForm Component

```jsx
// User preferences
- Theme toggle (light/dark) - future
- Language selection - future
- Date format preferences
- Timezone settings
- Dashboard layout options
```

### 6. NotificationSettings Component

```jsx
// Notification preferences
- Email notifications toggle
- Notification categories (checkboxes)
- Frequency settings
- Save preferences to backend
```

## Styling Guidelines

### Use existing SharedModalComponents

Import from `components/ui/SharedModalComponents.jsx`:

- `Input`, `Label`, `Button`, `Select`, `Checkbox`
- `FormSection`, `ErrorMessage`

### Match existing app styling

- Background: `bg-gray-50` for main, `bg-white` for sections
- Borders: `border-gray-200`
- Spacing: `p-4` or `p-6`
- Text: `text-gray-900` primary, `text-gray-500` secondary
- Focus states: `focus:ring-2 focus:ring-blue-500/30`

### Form styling

```jsx
// Input example
<Input
  name="first_name"
  value={formData.first_name}
  onChange={handleChange}
  className="w-full" // SharedModalComponents handles base styles
/>
```

## State Management

### Simple, flat state structure

```jsx
const [activeTab, setActiveTab] = useState('profile');
const [profile, setProfile] = useState({});
const [saving, setSaving] = useState(false);
const [errors, setErrors] = useState({});
```

### Form handling pattern

```jsx
const handleSubmit = async (e) => {
  e.preventDefault();
  setSaving(true);
  try {
    await updateUserProfile(user.id, formData);
    toast.success('Profile updated');
  } catch (error) {
    setErrors({ form: error.message });
  } finally {
    setSaving(false);
  }
};
```

## API Integration

Use existing API functions from `utils/api/users.js`:

- `updateUserProfile(userId, data)`
- `changeUserPassword(userId, newPassword)`
- `uploadUserAvatar(userId, formData)`

## Component Examples

### Tab Navigation

```jsx
<div className="border-b border-gray-200 mb-6">
  <nav className="-mb-px flex space-x-8">
    {['profile', 'security', 'preferences', 'notifications'].map(tab => (
      <button
        key={tab}
        onClick={() => setActiveTab(tab)}
        className={`
          py-2 px-1 border-b-2 font-medium text-sm capitalize
          ${activeTab === tab 
            ? 'border-blue-500 text-blue-600' 
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
        `}
      >
        {tab}
      </button>
    ))}
  </nav>
</div>
```

### Avatar Upload Zone

```jsx
<div className="relative group">
  <img 
    src={avatarUrl || '/default-avatar.png'} 
    className="h-32 w-32 rounded-full object-cover"
  />
  <label className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 rounded-full opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity">
    <input type="file" className="hidden" onChange={handleAvatarChange} />
    <i className="fas fa-camera text-white text-2xl" />
  </label>
</div>
```

## Implementation Priority

1. **Phase 1**: Basic structure
   - Replace Settings.jsx with tab navigation
   - Create ProfileCard and ProfileForm
   - Connect to existing APIs

2. **Phase 2**: Enhanced features
   - Add SecurityForm with password change
   - Improve avatar upload UX
   - Add form validation

3. **Phase 3**: Additional settings
   - PreferencesForm (prepare for future features)
   - NotificationSettings
   - Polish animations/transitions

## Migration Notes

1. Keep imports from existing Settings.jsx:
   - AuthContext usage
   - API function imports
   - Toast notifications

2. Remove/Replace:
   - Card components (use flat design)
   - Framer Motion (use CSS transitions)
   - Complex avatar state management

3. Ensure backward compatibility:
   - Same API endpoints
   - Same data structure
   - Same AuthContext updates

## Testing Checklist

- [ ] Profile updates save correctly
- [ ] Password change works
- [ ] Avatar upload/preview functions
- [ ] Form validation shows inline
- [ ] Responsive on mobile
- [ ] Tab navigation smooth
- [ ] Loading states display
- [ ] Error handling works
- [ ] Success messages show
- [ ] Context updates properly
