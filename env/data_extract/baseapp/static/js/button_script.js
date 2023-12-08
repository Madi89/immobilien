document.addEventListener('DOMContentLoaded', function () {

    document.getElementById("searchButton").addEventListener("click", function () {
        handleCityButtonClick('selectedCity', 'city');
    });

    document.getElementById("searchButton1").addEventListener("click", function () {
        handleRadiusButtonClick('zvgZIPorCity', 'selectedRadius', 'zvgR');
    });

    
    function handleCityButtonClick(elementId, type) {
        var selectedValue = document.getElementById(elementId).value;
        if (selectedValue) {
            const url = `/object_data/?${type}=${selectedValue}`;
            window.location.href = url;
        } else {
            alert('Bitte wählen Sie eine Stadt aus.');
        }
    }

    function handleRadiusButtonClick(inputId, elementId, type) {
        var userInput = document.getElementById(inputId).value;
        
        if (userInput) {
            var selectedValue = document.getElementById(elementId).value;
            const url = `/object_data_radius/?${type}=${selectedValue}&zvgZIPorCity=${encodeURIComponent(userInput)}`;
            window.location.href = url;
        } else {
            alert('Bitte geben Sie eine PLZ oder einen Ort ein.');
        }
    }
});

