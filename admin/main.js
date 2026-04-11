document.addEventListener('DOMContentLoaded', () => {
    // Basic navigation logic
    const navLinks = document.querySelectorAll('nav a');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            
            // In a real app, this would trigger page routing
            console.log(`Navigating to: ${link.textContent.trim()}`);
        });
    });

    // Animate stats cards on load
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = `all 0.5s ease ${index * 0.1}s`;
        
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 10);
    });

    // Mock search functionality
    const searchInput = document.querySelector('.search-bar input');
    searchInput.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
            const query = e.target.value.toLowerCase();
            alert(`Searching for: ${query}`);
            // Here you would filter the UI or call an API
        }
    });

    // Add table row hover effects or interactions
    const rows = document.querySelectorAll('tbody tr');
    rows.forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', (e) => {
            // Don't trigger row click if an action button was clicked
            if (e.target.closest('i')) return;
            
            const firstCell = row.cells[0].textContent;
            console.log(`Viewing details for: ${firstCell}`);
        });
    });

    // Delete Activity Logic
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const row = btn.closest('tr');
            const fileName = row.cells[0].textContent;
            if (confirm(`Are you sure you want to delete the record for ${fileName}?`)) {
                row.style.opacity = '0';
                row.style.transform = 'translateX(20px)';
                setTimeout(() => row.remove(), 300);
            }
        });
    });

    // Delete User Logic
    document.querySelectorAll('.delete-user-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const row = btn.closest('tr');
            const userName = row.cells[0].textContent;
            if (confirm(`CRITICAL: Are you sure you want to PERMANENTLY delete user ${userName}?`)) {
                row.style.opacity = '0';
                row.style.transform = 'scale(0.9)';
                setTimeout(() => row.remove(), 300);
            }
        });
    });
});
