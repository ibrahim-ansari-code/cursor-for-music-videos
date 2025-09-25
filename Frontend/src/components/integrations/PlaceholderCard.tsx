import React, { memo } from 'react';
import { PlaceholderCardProps } from '../../types/integrations';

const PlaceholderCard: React.FC<PlaceholderCardProps> = memo(({
  title = "More Integrations Coming Soon",
  description = "We're working on adding more integrations to help streamline your workflow.",
  icon = "fas fa-puzzle-piece",
  className = ""
}) => (
  <section
    className={`dark-panel rounded-lg border-2 border-dashed dark-divider ${className}`}
    role="region"
    aria-labelledby="upcoming-integrations-heading"
  >
    <div className="p-12 text-center">
      <div className="w-16 h-16 dark-input rounded-lg flex items-center justify-center mx-auto mb-4">
        <i className={`${icon} text-3xl text-gray-400 dark:text-gray-500`} aria-hidden="true" />
      </div>
      <h3 id="upcoming-integrations-heading" className="text-lg font-medium text-gray-800 dark:text-gray-100 mb-2">
        {title}
      </h3>
      <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
        {description}
      </p>
    </div>
  </section>
));

PlaceholderCard.displayName = 'PlaceholderCard';

export default PlaceholderCard;