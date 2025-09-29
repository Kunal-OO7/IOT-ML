const express = require("express");
const axios = require("axios");
const cors = require("cors");

const app = express();
app.use(cors());
app.use(express.json());

// Test route
app.get("/", (req, res) => {
    res.send("Backend is running");
});

// Route to call ML service
app.get("/predict", async (req, res) => {
    try {
        const response = await axios.get("http://127.0.0.1:8000/predict"); 
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: "ML service not reachable" });
    }
});

app.listen(6000, () => {
    console.log("Backend running on http://127.0.0.1:6000");
});