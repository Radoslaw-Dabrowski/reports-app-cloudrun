console.log('Script.js loaded');  // Debug log

document.addEventListener('DOMContentLoaded', function () {
    var setFrequenciesPopup = document.getElementById('setFrequenciesPopup');

    window.togglePopup = function () {
        if (setFrequenciesPopup && (setFrequenciesPopup.style.display === 'none' || setFrequenciesPopup.style.display === '')) {
            setFrequenciesPopup.style.display = 'block';
        } else if (setFrequenciesPopup) {
            setFrequenciesPopup.style.display = 'none';
        }
    };

    window.updateURL = function (param, value) {
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.set(param, value);
        window.location.search = urlParams.toString();
    };

    window.navigateMonth = function (offset) {
        const urlParams = new URLSearchParams(window.location.search);
        let month = parseInt(urlParams.get('month')) || currentMonth;
        let year = parseInt(urlParams.get('year')) || currentYear;

        month += offset;
        if (month > 12) {
            month = 1;
            year++;
        } else if (month < 1) {
            month = 12;
            year--;
        }

        urlParams.set('month', month);
        urlParams.set('year', year);
        window.location.search = urlParams.toString();
    };

    window.setToday = function () {
        const urlParams = new URLSearchParams(window.location.search);
        const today = new Date();
        urlParams.set('month', today.getMonth() + 1);
        urlParams.set('year', today.getFullYear());
        window.location.search = urlParams.toString();
    };
   
    document.getElementById('customerFilterVhealth')?.addEventListener('change', function() {
        console.log('Customer filter changed');
        filterTableVhealth();
    });
    
    document.getElementById('locationFilterVhealth')?.addEventListener('change', function() {
        console.log('Location filter changed');
        filterTableVhealth();
    });
    

    window.showLoading = function () {
        document.getElementById('loading').style.display = 'block';
    };

    window.removeFrequency = function (button) {
        var row = button.parentNode.parentNode;
        row.parentNode.removeChild(row);
    };

    window.addFrequency = function () {
        var tableBody = document.getElementById('frequencyTableBody');
        var newRow = document.createElement('tr');

        newRow.innerHTML = `
            <td><input type="text" class="form-control" name="report_name_new" value=""></td>
            <td>
                <select name="frequency_new" class="form-select">
                    <option value="none">None</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="quarterly">Quarterly</option>
                    <option value="annually">Annually</option>
                </select>
            </td>
            <td><input type="text" class="form-control" name="location_new" value=""></td>
            <td><button type="button" class="btn btn-danger" onclick="removeFrequency(this)">Remove</button></td>
        `;
        tableBody.appendChild(newRow);
    };

    window.toggleExcludeMissing = function () {
        const checkbox = document.getElementById('excludeMissing');
        // Save the state in localStorage instead of modifying the URL
        localStorage.setItem('excludeMissing', checkbox.checked);
        filterTable(); // Call your filter function to apply the state
    };

    window.startLongTask = function () {
        $('#loading').show();
        $.post('/run_long_task', function(data, status){
            if (status === 'success') {
                pollTaskStatus();
            } else {
                $('#loading').hide();
                alert('Task failed!');
            }
        });
    };

    window.refreshApp = function () {
        $('#loading').show();
        $.get('/refresh_cache', function(data, status){
            if (status === 'success') {
                location.reload();
            } else {
                $('#loading').hide();
                alert('Failed to refresh the app.');
            }
        });
    };

    window.showStatistics = function () {
        $.get('/show_statistics', function(data) {
            var statisticsTableBody = document.getElementById('statisticsTable').getElementsByTagName('tbody')[0];
            statisticsTableBody.innerHTML = '';
            data.forEach(function(alert) {
                var row = statisticsTableBody.insertRow();
                row.className = alert.color;
                row.innerHTML = `<td>${alert.date}</td><td>${alert.location}</td><td>${alert.critical}</td><td>${alert.immediate}</td><td>${alert.warning}</td><td>${alert.total}</td>`;
            });
            toggleStatisticsPopup();
        });
    };

    function pollTaskStatus() {
        $.get('/check_task_status', function(data) {
            if (data.task_running) {
                setTimeout(pollTaskStatus, 1000);
            } else {
                location.reload();
            }
        });
    };

    function togglePopup() {
        const popup = document.getElementById('setFrequenciesPopup');
        popup.style.display = (popup.style.display === 'block') ? 'none' : 'block';
    };
    
});

