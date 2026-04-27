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

// --- Google Login Logic ---
const GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID_HERE.apps.googleusercontent.com";

window.onload = function () {
    google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleCredentialResponse
    });
    
    const loginBtn = document.getElementById("google-login-button");
    const logoutBtn = document.getElementById("logout-btn");

    if (localStorage.getItem('access_token')) {
        loginBtn.style.display = 'none';
        logoutBtn.style.display = 'block';
    } else {
        google.accounts.id.renderButton(
            loginBtn,
            { theme: "outline", size: "large", type: "standard", shape: "pill" }
        );
    }

    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        location.reload();
    });
};

async function handleCredentialResponse(response) {
    console.log("Encoded JWT ID token: " + response.credential);
    
    // Send the token to your Django API
    try {
        const apiResponse = await fetch('/api/auth/google', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token: response.credential }),
        });

        const data = await apiResponse.json();

        if (apiResponse.ok) {
            console.log("Login successful!", data);
            localStorage.setItem('access_token', data.access);
            localStorage.setItem('refresh_token', data.refresh);
            alert(`Welcome, ${data.user.full_name}!`);
            location.reload(); // Reload to show logout button
        } else {
            alert("Login failed: " + data.error);
        }
    } catch (error) {
        console.error("Error during Google Login:", error);
    }
}
