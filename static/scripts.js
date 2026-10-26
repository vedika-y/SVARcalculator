
function openCalculator() {
    alert("Welcome to the SVaR Calculator!");
}
const form = document.getElementById("svarForm");

if (form) {
    form.addEventListener("submit", function(event) {
        event.preventDefault();

        const portfolio = Number(document.getElementById("portfolio").value);
        const confidence = document.getElementById("confidence").value;
        const period = document.getElementById("period").value;

        if (portfolio <= 0) {
            document.getElementById("result").textContent =
                "Please enter a valid portfolio value.";
            return;
        }

        document.getElementById("result").textContent =
            "Portfolio Value: ₹" + portfolio.toLocaleString("en-IN") +
            " | Confidence Level: " + confidence + "%" +
            " | Stress Period: " + period;
    });
}