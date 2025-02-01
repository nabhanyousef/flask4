document.addEventListener('DOMContentLoaded', function () {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const captureBtn = document.getElementById('capture-btn');
    const imageInput = document.getElementById('image-input');
    const uploadForm = document.getElementById('upload-form');

    // Access the camera
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
        })
        .catch(err => {
            console.error('Error accessing the camera: ', err);
        });

    // Draw ellipse on the video feed
    const drawEllipse = () => {
        const context = canvas.getContext('2d');
        context.clearRect(0, 0, canvas.width, canvas.height);

        // Draw the video frame
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Draw the ellipse
        context.beginPath();
        context.ellipse(
            canvas.width / 2, canvas.height / 2, // Center of the ellipse
            200, 150, // RadiusX and RadiusY
            0, 0, Math.PI * 2 // Rotation, start angle, end angle
        );
        context.strokeStyle = 'red';
        context.lineWidth = 3;
        context.stroke();
    };

    // Continuously draw the ellipse on the video feed
    setInterval(drawEllipse, 100);

    // Capture image
    captureBtn.addEventListener('click', function () {
        const context = canvas.getContext('2d');

        // Draw the video frame on the canvas
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Create a mask for the ellipse
        const mask = document.createElement('canvas');
        mask.width = canvas.width;
        mask.height = canvas.height;
        const maskContext = mask.getContext('2d');

        // Draw the ellipse on the mask
        maskContext.beginPath();
        maskContext.ellipse(
            canvas.width / 2, canvas.height / 2, // Center of the ellipse
            200, 150, // RadiusX and RadiusY
            0, 0, Math.PI * 2 // Rotation, start angle, end angle
        );
        maskContext.fillStyle = 'white';
        maskContext.fill();

        // Apply the mask to the image
        context.globalCompositeOperation = 'destination-in';
        context.drawImage(mask, 0, 0);

        // Convert the cropped image to base64
        const imageData = canvas.toDataURL('image/png');
        imageInput.value = imageData;

        // Show a success message
        alert('Image saved successfully!');

        // Submit the form
        uploadForm.submit();
    });
});