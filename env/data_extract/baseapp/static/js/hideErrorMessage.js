document.addEventListener("DOMContentLoaded", function() {
    var delay = 5000;
    setTimeout(function() {
        var errorMessage = document.querySelector('.error-message');
        if (errorMessage) {
            errorMessage.style.display = 'none';
        }
    }, delay);
});
