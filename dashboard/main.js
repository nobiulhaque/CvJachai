// Premium Dashboard Interactions
document.addEventListener('DOMContentLoaded', () => {
    console.log("CvJachai Intelligence Dashboard Initialized...");

    // Subtle Hover Effects for Cards
    const cards = document.querySelectorAll('.stat-card, .glass-section');
    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });

    // Delete Animations
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            if(confirm("Are you sure you want to remove this record from the intelligence pool?")) {
                const row = e.target.closest('tr');
                row.style.opacity = '0.5';
                row.style.filter = 'blur(2px)';
                setTimeout(() => {
                    row.remove();
                }, 300);
            }
        });
    });
});
