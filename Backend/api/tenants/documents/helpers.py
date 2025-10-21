"""
Tenant Document Taxonomy and Helper Functions

Defines the complete document type taxonomy organized into 14 categories
with 200+ specific document types. Provides validation and utility functions
for document categorization and metadata handling.

Categories:
1. Lease & Core Agreements (17 types)
2. Lease Addendums (15 types)
3. Condition & Inspections (7 types)
4. Province/Territory Forms (varies by province)
5. Commercial Tenant Files (22 types)
6. Applications & Screening/KYC (26 types)
7. Insurance & Risk (8 types)
8. Financial & Payments (15 types)
9. Maintenance/Unit-Level Work (10 types)
10. Legal Notices & Tribunal (17 types)
11. Communications & Records (9 types)
12. Move-In/Move-Out & Assets (14 types)
13. Privacy & Data Security (8 types)
14. Health/Safety/Accessibility (6 types)
"""

from typing import Dict, List, Optional, Any
from Backend.models.enums import DocumentCategory


# ============================================================================
# DOCUMENT TAXONOMY - 14 Categories with 200+ Specific Types
# ============================================================================

DOCUMENT_CATEGORIES: Dict[DocumentCategory, Dict[str, Any]] = {
    
    # ========== CATEGORY 1: LEASE & CORE AGREEMENTS ==========
    DocumentCategory.LEASE_AGREEMENTS: {
        "label": "Lease & Core Agreements",
        "icon": "DocumentText",
        "requires_expiry": False,
        "types": [
            "residential_tenancy_agreement",
            "guarantor_agreement",
            "cosigner_agreement",
            "lease_renewal_offer",
            "lease_renewal_acceptance",
            "fixed_term_end_notice",
            "non_renewal_letter",
            "mutual_termination_agreement",
            "early_termination_agreement",
            "rent_adjustment_notice",
            "rent_deferral_agreement",
            "rent_relief_agreement",
            "arrears_settlement_agreement",
            "house_rules_acknowledgment",
            "occupant_disclosure_form",
            "sublet_request",
            "assignment_request",
            "landlord_consent_sublet",
            "landlord_consent_assignment",
            "short_term_rental_request",
            "guest_use_request",
            "rent_incentive_addendum",
            "forwarding_address_form",
        ],
    },
    
    # ========== CATEGORY 2: LEASE ADDENDUMS ==========
    DocumentCategory.LEASE_ADDENDUMS: {
        "label": "Lease Addendums",
        "icon": "DocumentAdd",
        "requires_expiry": False,
        "types": [
            "addendum_parking",
            "addendum_storage",
            "addendum_locker",
            "addendum_pet_agreement",
            "addendum_smoking",
            "addendum_no_smoking",
            "addendum_utilities",
            "addendum_inclusions",
            "addendum_subletting_consent",
            "addendum_assignment_consent",
            "addendum_renovation",
            "addendum_alterations",
            "addendum_satellite",
            "addendum_antenna",
            "addendum_balcony",
            "addendum_bbq",
            "addendum_window_coverings",
            "addendum_noise",
            "addendum_keys_fobs",
            "addendum_amenity_use",
            "addendum_gym",
            "addendum_pool",
            "addendum_party_room",
            "addendum_accessibility_accommodation",
            "addendum_service_animal",
            "addendum_esa",
        ],
    },
    
    # ========== CATEGORY 3: CONDITION & INSPECTIONS ==========
    DocumentCategory.CONDITION_INSPECTIONS: {
        "label": "Condition & Inspections",
        "icon": "ClipboardCheck",
        "requires_expiry": False,
        "types": [
            "move_in_inspection_report",
            "move_out_inspection_report",
            "periodic_inspection_report",
            "deficiency_list_move_in",
            "deficiency_clearance_move_in",
            "unit_condition_photos_move_in",
            "unit_condition_photos_move_out",
        ],
    },
    
    # ========== CATEGORY 4: PROVINCE/TERRITORY FORMS ==========
    DocumentCategory.PROVINCE_FORMS: {
        "label": "Province/Territory Forms",
        "icon": "MapPin",
        "requires_expiry": False,
        "types": [
            # Ontario (ON)
            "on_standard_lease_rta",
            "on_n1_rent_increase",
            "on_n4_non_payment",
            "on_n5_disturbance",
            "on_n6_illegal_acts",
            "on_n7_impaired_safety",
            "on_n8_persistent_late_payment",
            "on_n9_tenant_notice_end",
            "on_n10_rent_increase_agreement",
            "on_n11_agreement_end_tenancy",
            "on_n12_landlord_own_use",
            "on_n13_demolition_repairs",
            "on_ltb_application_l1",
            "on_ltb_application_l2",
            "on_ltb_order",
            "on_ltb_decision",
            "on_proof_of_service",
            
            # British Columbia (BC)
            "bc_rtb1_tenancy_agreement",
            "bc_rtb7_rent_increase",
            "bc_rtb12_notice_end_tenancy",
            "bc_condition_inspection_move_in",
            "bc_condition_inspection_move_out",
            "bc_rtb_order",
            "bc_rtb_decision",
            "bc_proof_of_service",
            
            # Quebec (QC)
            "qc_tal_standard_lease",
            "qc_avis_modification_bail",
            "qc_avis_reprise_logement",
            "qc_resiliation_bail",
            "qc_etat_lieux_entree",
            "qc_etat_lieux_sortie",
            "qc_ordonnance_tal",
            "qc_preuve_signification",
            
            # Alberta (AB)
            "ab_14day_notice_terminate",
            "ab_24hour_notice_entry",
            "ab_notice_rent_increase",
            "ab_rtdrs_order",
            "ab_service_notice_record",
            
            # Manitoba (MB)
            "mb_rtb_tenancy_agreement",
            "mb_notice_rent_increase",
            "mb_order_possession",
            "mb_rtb_decision",
            "mb_service_record",
            
            # Saskatchewan (SK)
            "sk_ort_tenancy_agreement",
            "sk_rent_increase_notice",
            "sk_notice_vacate",
            "sk_ort_order",
            "sk_service_record",
            
            # Nova Scotia (NS)
            "ns_form_p_lease",
            "ns_notice_quit",
            "ns_entry_notice",
            "ns_rt_order",
            
            # New Brunswick (NB)
            "nb_standard_lease",
            "nb_notice_terminate",
            "nb_rent_increase_notice",
            "nb_rt_order",
            
            # Prince Edward Island (PE)
            "pe_lease_form",
            "pe_rent_increase_notice",
            "pe_termination_notice",
            "pe_order",
            
            # Newfoundland & Labrador (NL)
            "nl_lease_form",
            "nl_rent_increase_notice",
            "nl_termination_notice",
            "nl_order",
            
            # Territories (YT, NT, NU)
            "territories_standard_lease",
            "territories_rent_increase",
            "territories_termination_notice",
            "territories_tribunal_order",
            "territories_proof_of_service",
        ],
    },
    
    # ========== CATEGORY 5: COMMERCIAL TENANT FILES ==========
    DocumentCategory.COMMERCIAL_FILES: {
        "label": "Commercial Tenant Files",
        "icon": "Briefcase",
        "requires_expiry": False,
        "types": [
            "commercial_lease_triple_net",
            "commercial_lease_gross",
            "commercial_lease_modified_gross",
            "offer_to_lease",
            "letter_of_intent",
            "rent_schedule_addendum",
            "percentage_rent_addendum",
            "exclusive_use_clause",
            "radius_clause",
            "option_to_renew",
            "option_to_extend",
            "option_to_expand",
            "personal_guarantee",
            "corporate_guarantee",
            "snda_agreement",
            "estoppel_certificate",
            "sublease_agreement",
            "landlord_consent_assignment",
            "premises_surrender_agreement",
            "tenant_signage_approval",
            "health_permit",
            "liquor_licence",
            "hazardous_materials_declaration",
            "tenant_fitout_drawings",
            "tenant_fitout_permit",
            "as_built_drawings",
            "commissioning_certificates",
        ],
    },
    
    # ========== CATEGORY 6: APPLICATIONS & SCREENING/KYC ==========
    DocumentCategory.APPLICATIONS_KYC: {
        "label": "Applications & Screening/KYC",
        "icon": "UserCheck",
        "requires_expiry": False,
        "types": [
            "residential_rental_application",
            "commercial_tenancy_application",
            "consent_credit_check",
            "consent_background_check",
            "drivers_licence_id",
            "passport_id",
            "pr_card_id",
            "sin_verification_form",
            "proof_income_pay_stub",
            "proof_income_employment_letter",
            "proof_income_tax_return",
            "proof_income_t1_noa",
            "proof_funds_bank_statement",
            "reference_letter_employer",
            "reference_letter_landlord",
            "cosigner_id",
            "guarantor_id",
            "incorporation_certificate",
            "articles_of_incorporation",
            "business_licence",
            "gst_hst_registration",
            "qst_registration",
            "corporate_financial_statements",
            "credit_report_commercial",
            "beneficial_ownership_declaration",
        ],
    },
    
    # ========== CATEGORY 7: INSURANCE & RISK ==========
    DocumentCategory.INSURANCE_RISK: {
        "label": "Insurance & Risk",
        "icon": "Shield",
        "requires_expiry": True,  # Insurance documents typically expire
        "types": [
            "tenant_insurance_certificate",
            "tenant_insurance_renewal",
            "business_interruption_policy",
            "general_liability_certificate",
            "environmental_liability_policy",
            "incident_claim_report",
            "insurance_waiver",
            "vehicle_insurance_parking",
        ],
    },
    
    # ========== CATEGORY 8: FINANCIAL & PAYMENTS ==========
    DocumentCategory.FINANCIAL_PAYMENTS: {
        "label": "Financial & Payments",
        "icon": "CurrencyDollar",
        "requires_expiry": False,
        "types": [
            "security_deposit_receipt",
            "key_deposit_receipt",
            "monthly_rent_receipt",
            "pad_form",
            "ach_authorization",
            "credit_card_authorization",
            "payment_plan_agreement",
            "chargeback_notice",
            "nsf_notice",
            "tenant_ledger_export",
            "year_end_rent_summary",
            "rl31_releve_qc",
            "statement_of_arrears",
            "settlement_of_account_letter",
            "collections_referral_notice",
        ],
    },
    
    # ========== CATEGORY 9: MAINTENANCE/UNIT-LEVEL WORK ==========
    DocumentCategory.MAINTENANCE_WORK: {
        "label": "Maintenance/Unit-Level Work",
        "icon": "Wrench",
        "requires_expiry": False,
        "types": [
            "maintenance_request_export",
            "work_order_unit",
            "vendor_quote_unit",
            "maintenance_invoice_tenant_billed",
            "before_photos_unit",
            "after_photos_unit",
            "preventive_maintenance_log",
            "pest_control_log",
            "environmental_report_unit",
            "access_authorization_vendor",
        ],
    },
    
    # ========== CATEGORY 10: LEGAL NOTICES & TRIBUNAL ==========
    DocumentCategory.LEGAL_NOTICES: {
        "label": "Legal Notices & Tribunal",
        "icon": "Scale",
        "requires_expiry": False,
        "types": [
            "notice_of_entry_unit",
            "policy_violation_noise",
            "policy_violation_smoking",
            "policy_violation_pet",
            "parking_violation_notice",
            "warning_letter",
            "breach_notice",
            "payment_demand_3day",
            "payment_demand_14day",
            "payment_demand_30day",
            "tribunal_application_tenant_copy",
            "tribunal_order_tenant_copy",
            "settlement_agreement",
            "minutes_of_settlement",
            "record_of_service",
            "sheriff_bailiff_notice",
        ],
    },
    
    # ========== CATEGORY 11: COMMUNICATIONS & RECORDS ==========
    DocumentCategory.COMMUNICATIONS: {
        "label": "Communications & Records",
        "icon": "ChatBubble",
        "requires_expiry": False,
        "types": [
            "tenant_correspondence_email",
            "sms_transcript_export",
            "lease_renewal_invitation",
            "lease_renewal_response",
            "insurance_reminder_notice",
            "maintenance_appointment_confirmation",
            "emergency_alert_notice",
            "call_log_notes",
            "ai_chat_transcript",
        ],
    },
    
    # ========== CATEGORY 12: MOVE-IN/MOVE-OUT & ASSETS ==========
    DocumentCategory.MOVE_IN_OUT: {
        "label": "Move-In/Move-Out & Assets",
        "icon": "Truck",
        "requires_expiry": False,
        "types": [
            "keys_fobs_agreement",
            "parking_permit",
            "parking_registration",
            "vehicle_registration_parking",
            "bike_storage_agreement",
            "mailbox_assignment",
            "parcel_locker_assignment",
            "utility_meter_reading_move_in",
            "utility_meter_reading_move_out",
            "utility_account_confirmation",
            "internet_cable_authorization",
            "appliance_manuals_unit",
            "appliance_serial_numbers",
            "unit_turn_checklist",
            "damage_settlement_agreement",
            "cleaning_acknowledgment",
        ],
    },
    
    # ========== CATEGORY 13: PRIVACY & DATA SECURITY ==========
    DocumentCategory.PRIVACY_SECURITY: {
        "label": "Privacy & Data Security",
        "icon": "LockClosed",
        "requires_expiry": False,
        "types": [
            "privacy_consent_pipeda",
            "privacy_consent_law25",
            "data_processing_consent",
            "background_check_consent",
            "credit_check_consent",
            "photo_video_consent",
            "ai_review_acknowledgment",
            "data_access_request",
            "data_deletion_request",
        ],
    },
    
    # ========== CATEGORY 14: HEALTH/SAFETY/ACCESSIBILITY ==========
    DocumentCategory.HEALTH_SAFETY: {
        "label": "Health/Safety/Accessibility",
        "icon": "Heart",
        "requires_expiry": True,  # Some documents like ESA letters may expire
        "types": [
            "service_animal_documentation",
            "esa_letter",
            "vaccination_record_pet",
            "accessibility_accommodation_request",
            "medical_accommodation_letter",
            "emergency_contact_form",
            "emergency_preparedness_acknowledgment",
        ],
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_categories() -> List[Dict[str, Any]]:
    """
    Return list of all document categories with metadata.
    
    Returns:
        List of dicts with category info (key, label, icon, requires_expiry, types)
        
    Example:
        >>> categories = get_all_categories()
        >>> print(categories[0])
        {
            "key": "lease_agreements",
            "label": "Lease & Core Agreements",
            "icon": "DocumentText",
            "requires_expiry": False,
            "types": ["residential_tenancy_agreement", ...]
        }
    """
    return [
        {
            "key": category.value,
            "label": info["label"],
            "icon": info["icon"],
            "requires_expiry": info["requires_expiry"],
            "types": info["types"],
        }
        for category, info in DOCUMENT_CATEGORIES.items()
    ]


def get_types_for_category(category: DocumentCategory) -> List[str]:
    """
    Get list of document types within a specific category.
    
    Args:
        category: DocumentCategory enum value
        
    Returns:
        List of document type strings
        
    Raises:
        KeyError: If category doesn't exist
        
    Example:
        >>> types = get_types_for_category(DocumentCategory.INSURANCE_RISK)
        >>> print(types)
        ["tenant_insurance_certificate", "tenant_insurance_renewal", ...]
    """
    return DOCUMENT_CATEGORIES[category]["types"]


def validate_document_type(category: DocumentCategory, document_type: str) -> bool:
    """
    Validate that a document type exists within a category.
    
    Args:
        category: DocumentCategory enum value
        document_type: Specific document type string
        
    Returns:
        True if valid, False otherwise
        
    Example:
        >>> is_valid = validate_document_type(
        ...     DocumentCategory.INSURANCE_RISK,
        ...     "tenant_insurance_certificate"
        ... )
        >>> print(is_valid)
        True
    """
    try:
        return document_type in DOCUMENT_CATEGORIES[category]["types"]
    except KeyError:
        return False


def requires_expiry_tracking(category: DocumentCategory) -> bool:
    """
    Check if a category typically requires expiry date tracking.
    
    Args:
        category: DocumentCategory enum value
        
    Returns:
        True if expiry tracking recommended, False otherwise
        
    Example:
        >>> needs_expiry = requires_expiry_tracking(DocumentCategory.INSURANCE_RISK)
        >>> print(needs_expiry)
        True
    """
    try:
        return DOCUMENT_CATEGORIES[category]["requires_expiry"]
    except KeyError:
        return False


def get_category_icon(category: DocumentCategory) -> str:
    """
    Get the icon name for a category.
    
    Args:
        category: DocumentCategory enum value
        
    Returns:
        Icon name string (Heroicons format)
        
    Example:
        >>> icon = get_category_icon(DocumentCategory.INSURANCE_RISK)
        >>> print(icon)
        Shield
    """
    try:
        return DOCUMENT_CATEGORIES[category]["icon"]
    except KeyError:
        return "Document"  # Default icon


def get_category_label(category: DocumentCategory) -> str:
    """
    Get the human-readable label for a category.
    
    Args:
        category: DocumentCategory enum value
        
    Returns:
        Label string
        
    Example:
        >>> label = get_category_label(DocumentCategory.INSURANCE_RISK)
        >>> print(label)
        Insurance & Risk
    """
    try:
        return DOCUMENT_CATEGORIES[category]["label"]
    except KeyError:
        return category.value.replace("_", " ").title()


def suggest_tags_for_type(category: DocumentCategory, document_type: str) -> List[str]:
    """
    Suggest default tags based on document category and type.
    
    Args:
        category: DocumentCategory enum value
        document_type: Specific document type
        
    Returns:
        List of suggested tag strings
        
    Example:
        >>> tags = suggest_tags_for_type(
        ...     DocumentCategory.INSURANCE_RISK,
        ...     "tenant_insurance_certificate"
        ... )
        >>> print(tags)
        ["compliance", "insurance", "annual"]
    """
    tags = [category.value.replace("_", "-")]  # Category as tag
    
    # Add compliance tag if expiry tracking required
    if requires_expiry_tracking(category):
        tags.append("compliance")
    
    # Add type-specific suggestions
    if "insurance" in document_type:
        tags.append("insurance")
    if "renewal" in document_type:
        tags.append("renewal")
    if "notice" in document_type:
        tags.append("notice")
    if "agreement" in document_type:
        tags.append("agreement")
    
    return list(set(tags))  # Remove duplicates


def get_total_document_types() -> int:
    """
    Get total count of all document types across all categories.
    
    Returns:
        Total number of document types
    """
    return sum(len(info["types"]) for info in DOCUMENT_CATEGORIES.values())


# ============================================================================
# MODULE METADATA
# ============================================================================

__all__ = [
    "DOCUMENT_CATEGORIES",
    "get_all_categories",
    "get_types_for_category",
    "validate_document_type",
    "requires_expiry_tracking",
    "get_category_icon",
    "get_category_label",
    "suggest_tags_for_type",
    "get_total_document_types",
]

