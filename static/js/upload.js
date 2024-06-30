// Select DOM elements
const button = document.querySelector(".button");
const submit = document.querySelector(".submit");
const name1 = document.querySelector("#name");
const roll = document.querySelector("#roll");
const imageData = document.querySelector("#imageData");
const image = document.querySelector("#image");
const video = document.querySelector("#video");

// Toggle button class based on inputs
function toggleClass() {
  if (
    name1.value !== "" &&
    roll.value !== "" &&
    (image.files.length > 0 || imageData.value !== "")
  ) {
    this.classList.add("active");
  } else {
    this.classList.remove("active");
  }
}

// Add finished class to button
function addClass() {
  if (this.classList.contains("active")) {
    this.classList.add("finished");
  }
}

button.addEventListener("click", toggleClass);
button.addEventListener("transitionend", toggleClass);
button.addEventListener("transitionend", addClass);

// Read uploaded file URL
function readURL(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function (e) {
      document.querySelector(".image-upload-wrap").style.display = "none";
      document.querySelector(".file-upload-image").src = e.target.result;
      document.querySelector(".file-upload-content").style.display = "block";
      document.querySelector(".image-title").textContent = input.files[0].name;
    };
    reader.readAsDataURL(input.files[0]);
  } else {
    removeUpload();
  }
}

// Open camera for video capture
function openCamera() {
  navigator.mediaDevices
    .getUserMedia({ video: true })
    .then(function (stream) {
      video.srcObject = stream;
      video.play();
    })
    .catch(function (err) {
      console.log("An error occurred: " + err);
    });
}

// Capture image from video stream
function captureImage() {
  let canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const context = canvas.getContext("2d");
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  let base64data = canvas.toDataURL("image/jpg");
  imageData.value = base64data;

  document.querySelector(".file-upload-image").src = base64data;
  document.querySelector(".file-upload-content").style.display = "block";
  document.querySelector(".image-upload-wrap").style.display = "none";

  video.pause();
  video.srcObject.getVideoTracks()[0].stop();
}

// Validate form submission
document.querySelector("form").addEventListener("submit", function (event) {
  if (imageData.value === "" && image.files.length === 0) {
    alert("Please capture or upload an image.");
    event.preventDefault();
  }
});

// Remove uploaded file
function removeUpload() {
  imageData.value = "";
  const fileInput = document.querySelector(".file-upload-input");
  fileInput.replaceWith(fileInput.cloneNode(true));
  document.querySelector(".file-upload-content").style.display = "none";
  document.querySelector(".image-upload-wrap").style.display = "block";
}

// Bind drag events
document
  .querySelector(".image-upload-wrap")
  .addEventListener("dragover", function () {
    this.classList.add("image-dropping");
  });
document
  .querySelector(".image-upload-wrap")
  .addEventListener("dragleave", function () {
    this.classList.remove("image-dropping");
  });

// Toggle button class on click
button.addEventListener("click", function () {
  if (
    name1.value != "" &&
    roll.value != "" &&
    (document.querySelector("#image").files.length > 0 ||
      imageData.value !== "")
  ) {
    this.classList.add("active");
  }
});
