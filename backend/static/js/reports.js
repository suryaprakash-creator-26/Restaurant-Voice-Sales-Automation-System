async function loadDashboard() {

    const response =
        await fetch("/analytics");

    const data =
        await response.json();

    document.getElementById("revenueCard")
        .innerText =
        "₹" + data.monthly_total.toLocaleString();

    document.getElementById("topFoodCard")
        .innerText =
        data.top_food;

    document.getElementById("unitsCard")
        .innerText =
        data.total_units;

    document.getElementById("avgCard")
        .innerText =
        "₹" + data.avg_daily_sales;

    

    document.getElementById("activeCard")
        .innerText =
        data.active_foods;

    createRevenueChart(data);

    createFoodChart(data);

    loadTopFoods(data);

    loadLowFoods(data);

    loadInsights(data);
}

function createRevenueChart(data){

    new Chart(
        document.getElementById("salesChart"),
        {
            type:"bar",

            data:{
                labels:data.dates,

                datasets:[{
                    label:"Revenue",
                    data:data.totals
                }]
            }
        }
    );
}

function createFoodChart(data){

    const labels = [];
    const values = [];

    Object.entries(data.foods).forEach(
        ([food,qty])=>{

            if(qty>0){

                labels.push(food);
                values.push(qty);

            }

        }
    );

    new Chart(
        document.getElementById("foodChart"),
        {
            type:"doughnut",

            data:{
                labels:labels,

                datasets:[{
                    data:values
                }]
            }
        }
    );
}

function loadTopFoods(data){

    let html = "";

    data.top_foods.forEach(
        (item,index)=>{

            html += `
            <tr>
                <td>${index+1}</td>
                <td>${item[0]}</td>
                <td>${item[1]}</td>
            </tr>`;
        }
    );

    document.getElementById(
        "topFoodsTable"
    ).innerHTML = html;
}

function loadLowFoods(data){

    const colors = [
        "#6366F1", // Indigo
        "#EC4899", // Pink
        "#06B6D4", // Cyan
        "#10B981", // Emerald
        "#F59E0B", // Amber
        "#8B5CF6", // Purple
        "#EF4444", // Red
        "#14B8A6"  // Teal
    ];

    document.getElementById(
        "noSalesFoods"
    ).innerHTML =
    data.no_sales_foods
    .map(food => `
        <div class="food-row">
            ${food}
        </div>
    `)
    .join("");

    document.getElementById(
        "lowSalesFoods"
    ).innerHTML =
    data.low_sales_foods
    .map((item,index) => `
        <div class="low-card"
             style="border-top:5px solid ${colors[index % colors.length]}">

            <div class="sold-count">
                ${item.qty}
            </div>

            <div class="sold-text">
                SOLD
            </div>

            <div class="food-title"
                 style="color:${colors[index % colors.length]}">
                ${item.food}
            </div>

            <div class="food-status">
                Requires Promotion
            </div>

        </div>
    `)
    .join("");
}

function loadInsights(data){

    const cards = [

        {
            title:"TOP SELLER",
            text:`${data.top_food} is the best selling item.`
        },

        {
            title:"REVENUE",
            text:`Monthly revenue is ₹${data.monthly_total}.`
        },

        {
            title:"MENU STATUS",
            text:`${data.no_sales_foods.length} items generated no sales.`
        }

    ];

    document.getElementById(
        "insights"
    ).innerHTML =
    cards.map(card => `
        <div class="insight-card">

            <h4>${card.title}</h4>

            <p>${card.text}</p>

        </div>
    `).join("");
}

loadDashboard();