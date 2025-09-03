export const SORT_OPTIONS = [
  { id: 'name-asc', label: 'A to Z', icon: 'fas fa-sort-alpha-down' },
  { id: 'name-desc', label: 'Z to A', icon: 'fas fa-sort-alpha-down-alt' },
  { id: 'type-asc', label: 'A to Z', icon: 'fas fa-sort-alpha-down' },
  { id: 'type-desc', label: 'Z to A', icon: 'fas fa-sort-alpha-down-alt' },
  { id: 'status-asc', label: 'A to Z', icon: 'fas fa-sort-alpha-down' },
  { id: 'status-desc', label: 'Z to A', icon: 'fas fa-sort-alpha-down-alt' },
  { id: 'date-desc', label: 'Newest First', icon: 'fas fa-sort-numeric-down-alt' },
  { id: 'date-asc', label: 'Oldest First', icon: 'fas fa-sort-numeric-down' },
] as const;

export const SORT_SECTIONS = [
  {
    title: 'Name',
    options: [
      { id: 'name-asc', label: 'A to Z', icon: 'fas fa-sort-alpha-down' },
      { id: 'name-desc', label: 'Z to A', icon: 'fas fa-sort-alpha-down-alt' },
    ],
  },
  {
    title: 'Type',
    options: [
      { id: 'type-asc', label: 'A to Z', icon: 'fas fa-sort-alpha-down' },
      { id: 'type-desc', label: 'Z to A', icon: 'fas fa-sort-alpha-down-alt' },
    ],
  },
  {
    title: 'Status',
    options: [
      { id: 'status-asc', label: 'A to Z', icon: 'fas fa-sort-alpha-down' },
      { id: 'status-desc', label: 'Z to A', icon: 'fas fa-sort-alpha-down-alt' },
    ],
  },
  {
    title: 'Date Added',
    options: [
      { id: 'date-desc', label: 'Newest First', icon: 'fas fa-sort-numeric-down-alt' },
      { id: 'date-asc', label: 'Oldest First', icon: 'fas fa-sort-numeric-down' },
    ],
  },
] as const;

export type SortOption = typeof SORT_OPTIONS[number]['id'];