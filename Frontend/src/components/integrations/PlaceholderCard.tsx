import React, { memo } from 'react';
import { PlaceholderCardProps } from '../../types/integrations';

const PlaceholderCard: React.FC<PlaceholderCardProps> = memo(({
  title = "More Integrations Coming Soon",
  description = "We're working on adding more integrations to help streamline your workflow.",
  icon = "fas fa-puzzle-piece",
  className = ""
}) => (
  <section
    className={`bg-white rounded-lg border-2 border-dashed border-gray-300 ${className}`}
    role="region"
    aria-labelledby="upcoming-integrations-heading"
  >
    <div className="p-12 text-center">
      <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center mx-auto mb-4">
        <i className={`${icon} text-3xl text-gray-400`} aria-hidden="true" />
      </div>
      <h3 id="upcoming-integrations-heading" className="text-lg font-medium text-gray-800 mb-2">
        {title}
      </h3>
      <p className="text-gray-500 max-w-md mx-auto">
        {description}
      </p>
    </div>
  </section>
));

PlaceholderCard.displayName = 'PlaceholderCard';

export default PlaceholderCard;