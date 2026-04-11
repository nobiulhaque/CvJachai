# CvJachai Admin Dashboard

This is a premium, modern frontend UI for the CvJachai administrative dashboard. 

## Features
- **Overview Dashboard**: At-a-glance statistics of resume processing.
- **Classification Tracker**: Real-time view of recent CV classifications.
- **Glassmorphism UI**: Modern aesthetic with blur effects and vibrant gradients.
- **Responsive Design**: Optimized for desktops and tablets.

## Structure
- `index.html`: Main layout and structure.
- `style.css`: Premium design system and component styles.
- `main.js`: Interactive elements and UI logic.

## Integration
To connect this with the Django backend:
1. Move these files to a `templates/admin` directory if using Django templates.
2. Use the Django REST Framework endpoints from the `api` app to populate the data.
3. Configure authentication to ensure only administrators can access this folder.
