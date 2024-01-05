function handleCityButtonClick(elementId) {
    var selectedValue = document.getElementById(elementId).value;
    
    if (selectedValue !== '--- Bitte wählen ---') {
        const url = `/object_data/?city=${selectedValue}`;
        window.location.href = url;
    } else {
        showAlert('Bitte wählen Sie eine Stadt aus.');
       }
}

document.addEventListener('DOMContentLoaded', function () {
    document.getElementById("searchButton").addEventListener("click", _.debounce(function () {
        console.log('searchButton clicked');
        handleCityButtonClick('city');
    }, 500));
});


function handleRadiusButtonClick(inputId, elementId, type) {
    var userInput = document.getElementById(inputId).value;
    
    if (userInput) {
        var selectedValue = document.getElementById(elementId).value;
        const url = `/object_data_radius/?${type}=${selectedValue}&zvgZIPorCity=${encodeURIComponent(userInput)}`;
        window.location.href = url;
    } else {
        showAlert('Bitte geben Sie eine PLZ oder einen Ort ein.');
    }
}

document.addEventListener('DOMContentLoaded', function () {
    document.getElementById("searchButton1").addEventListener("click", _.debounce(function () {
        console.log('searchButton1 clicked');
        handleRadiusButtonClick('zvgZIPorCity', 'selectedRadius', 'zvgR');
    }, 500));
});


function showAlert(message) {
    var modal = document.getElementById('customAlert');
    var alertMessage = document.getElementById('alertMessage');
    
    alertMessage.textContent = message;
    modal.style.display = 'block';

    setTimeout(function () {
        modal.style.display = 'none';
    }, 3000);

    var closeButton = document.querySelector('.close');
    closeButton.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}