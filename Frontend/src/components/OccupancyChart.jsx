import React, { useRef, useEffect } from "react";
import Chart from "chart.js/auto";

const OccupancyChart = ({ occupied, vacant }) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = chartRef.current.getContext("2d");

    chartInstance.current = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Occupied", "Vacant"],
        datasets: [
          {
            data: [occupied, vacant],
            backgroundColor: [
              "#10B981", // green-500
              "#3B82F6", // blue-500
            ],
            borderColor: ["#FFFFFF", "#FFFFFF"],
            borderWidth: 2,
            hoverOffset: 4,
          },
        ],
      },
      options: {
        cutout: "70%",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                const total = context.dataset.data.reduce(
                  (acc, val) => acc + val,
                  0
                );
                const value = context.raw;
                const percentage = Math.round((value / total) * 100);
                return `${context.label}: ${value} (${percentage}%)`;
              },
            },
          },
        },
      },
    });

    // Center text plugin
    Chart.register({
      id: "centerText",
      beforeDraw: function (chart) {
        if (chart.config.type === "doughnut") {
          // Get ctx from chart
          const ctx = chart.ctx;

          // Get options from the center object in options
          const total = chart.data.datasets[0].data.reduce(
            (acc, val) => acc + val,
            0
          );

          // Set text alignment and font size
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";

          // Position and draw the text
          const centerX = (chart.chartArea.left + chart.chartArea.right) / 2;
          const centerY = (chart.chartArea.top + chart.chartArea.bottom) / 2;

          // Draw total units
          ctx.font = "700 24px Inter";
          ctx.fillStyle = "#1F2937"; // gray-800
          ctx.fillText(`${total}`, centerX, centerY - 10);

          // Draw "Units" text
          ctx.font = "500 14px Inter";
          ctx.fillStyle = "#6B7280"; // gray-500
          ctx.fillText("Units", centerX, centerY + 15);
        }
      },
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [occupied, vacant]);

  return (
    <div className="h-60 w-full">
      <canvas ref={chartRef}></canvas>
    </div>
  );
};

export default OccupancyChart;
