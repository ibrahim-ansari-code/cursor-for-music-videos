import React from "react";
import RentTracker from "../RentTracker";
import { useAccounting } from "./AccountingContext";

const RentTrackerTab = () => {
  const { setAccountingData } = useAccounting();

  return (
    <RentTracker
      onDataLoaded={(data) => {
        // Validate that data is an array before processing
        if (!Array.isArray(data)) {
          console.warn("RentTrackerTab: Expected data to be an array, but received:", typeof data);
          // Set default values when data is not an array
          setAccountingData((prevData) => ({
            ...prevData,
            snapshot: {
              ...prevData.snapshot,
              paidRent: 0,
              totalRent: 0,
            },
          }));
          return;
        }

        // Update the rent tracker metrics when data is loaded from the RentTracker component
        // Calculate actual rent amounts instead of just counting entries
        const totalRent = data.reduce((sum, rent) => sum + (parseFloat(rent.monthly_rent) || 0), 0);
        const paidRent = data
          .filter((rent) => rent.status === "PAID")
          .reduce((sum, rent) => {
            // Only use amount_paid if it exists and is valid, otherwise use 0
            // Using monthly_rent as fallback could lead to incorrect calculations for partial payments
            const amountPaid = parseFloat(rent.amount_paid) || 0;
            return sum + amountPaid;
          }, 0);

        setAccountingData((prevData) => ({
          ...prevData,
          snapshot: {
            ...prevData.snapshot,
            paidRent,
            totalRent,
          },
        }));
      }}
    />
  );
};

export default RentTrackerTab;