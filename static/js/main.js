document.addEventListener("DOMContentLoaded", () => {
    const nutritionHealthy = document.getElementById("healthyFoods");
    const nutritionJunk = document.getElementById("junkFoods");

    fetch("/api/nutrition")
        .then(res => res.json())
        .then(data => {
            if (data.success) renderNutrition(data.foods);
            else alert(data.message || "Failed to load food data");
        })
        .catch(() => alert("Error loading nutrition data"));

    function renderNutrition(foods) {
        nutritionHealthy.innerHTML = "";
        nutritionJunk.innerHTML = "";

        foods.forEach(food => {
            const card = document.createElement("div");
            const foodClass = food.name.toLowerCase().replace(/\s+/g, "_").replace(/\(.*?\)/g, "").replace(/\./g,"");

            card.classList.add("food-card", food.type, foodClass);

            card.innerHTML = `
                <h3>${food.name}</h3>
                <p class="desc">${food.description}</p>
                <p><b>Calories:</b> ${food.calories}</p>
                <p><b>Protein:</b> ${food.protein}g</p>
                <p><b>Fat:</b> ${food.fat}g</p>
                <p><b>Carbs:</b> ${food.carbs}g</p>
            `;

            if (food.type === "healthy") nutritionHealthy.appendChild(card);
            else nutritionJunk.appendChild(card);
        });
    }
});
