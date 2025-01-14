document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('add-entry-form');
    const thumbRobo = document.getElementById('thumb-robo');

    if (!form) {
        console.error('Form with id "add-entry-form" not found');
        return;
    }

    if (!thumbRobo) {
        console.error('Image with id "thumb-robo" not found');
        return;
    }

    console.log('DOM fully loaded and parsed');
    console.log('Form:', form);
    console.log('Thumb Robo:', thumbRobo);

    form.addEventListener('submit', (event) => {
        // Prevent default submission for animation
        event.preventDefault();

        console.log('Form submitted');

        // Trigger fade-in-out animation
        thumbRobo.classList.remove('hidden');
        thumbRobo.classList.add('fade-in-out');

        // Wait for animation to complete before form submission
        setTimeout(() => {
            thumbRobo.classList.remove('fade-in-out');
            thumbRobo.classList.add('hidden');
            form.submit(); // Proceed with form submission
        }, 2000); // Matches the animation duration
    });
});