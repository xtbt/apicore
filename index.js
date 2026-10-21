function imprimirDatos() {
    var dato1 = document.getElementById("txtDato1").value;
    var dato2 = document.getElementById("txtDato2").value;
    console.log("Dato 1: " + dato1 + "\nDato 2: " + dato2);

    fetch('http://localhost:5000/moods', {
        method: 'GET',
    })
    .then(response => response.json())
    .then(data => {
        console.log(data);
        document.getElementById("preDatos").textContent = JSON.stringify(data, null, 2);
    })
    .catch(error => {
        console.error('Error:', error);
    });
}