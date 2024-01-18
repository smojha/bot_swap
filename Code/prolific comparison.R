
##### Compare Prolific with lab participants

# Load necessary library
library(dplyr)
library(openxlsx)

# Import the data
data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/orders_2023-11-30.csv')

# Split data into two groups: selected traders and others
selected_traders <- data %>% filter(part_label %in% c("86T", "04R")) # Prolific participants
other_traders <- data %>% filter(!part_label %in% c("86T", "04R")) # Lab participants

# Define a function to calculate the metrics
calculate_metrics <- function(df) {
  df %>% 
    group_by(round_number) %>% 
    summarize(
      avg_buy_price = ifelse(sum(type == "BUY") > 0, mean(price[type == "BUY"], na.rm = TRUE), 0),
      avg_sell_price = ifelse(sum(type == "SELL") > 0, mean(price[type == "SELL"], na.rm = TRUE), 0),
      num_buy_orders = sum(type == "BUY"),
      num_sell_orders = sum(type == "SELL"),
      total_quantity = sum(quantity_final),
      avg_quantity = mean(quantity_final)
    )
}


# Define a function to calculate overall metrics
calculate_overall_metrics <- function(df) {
  df %>% 
    summarize(
      overall_avg_buy_price = ifelse(sum(type == "BUY") > 0, mean(price[type == "BUY"], na.rm = TRUE), 0),
      overall_avg_sell_price = ifelse(sum(type == "SELL") > 0, mean(price[type == "SELL"], na.rm = TRUE), 0),
      overall_num_buy_orders = sum(type == "BUY"),
      overall_num_sell_orders = sum(type == "SELL"),
      overall_total_quantity = sum(quantity_final)
    )
}


# Calculate metrics for each group by round
metrics_selected_traders <- calculate_metrics(selected_traders)
metrics_other_traders <- calculate_metrics(other_traders)


# Calculate overall metrics for each group
overall_metrics_selected <- calculate_overall_metrics(selected_traders)
overall_metrics_others <- calculate_overall_metrics(other_traders)

  
# Print the results
print(metrics_selected_traders)
print(metrics_other_traders)
print(overall_metrics_selected)
print(overall_metrics_others)

# Save files:
# Create a new workbook
wb <- createWorkbook()

# Add sheets with data
addWorksheet(wb, "Metrics selected traders")
writeData(wb, "Metrics selected traders", metrics_selected_traders)

# Add sheets with data
addWorksheet(wb, "Metrics other traders")
writeData(wb, "Metrics other traders", metrics_other_traders)

# Add sheets with data
addWorksheet(wb, "Overall metrics selected")
writeData(wb, "Overall metrics selected", overall_metrics_selected)

# Add sheets with data
addWorksheet(wb, "Overall metrics others")
writeData(wb, "Overall metrics others", overall_metrics_others)

# Save the workbook
saveWorkbook(wb, "/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/Prolific.xlsx", overwrite = TRUE)



## Forecast comparison

# Import the data
data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/rounds_2023-11-30.csv')
forecast_data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/rounds_2023-11-30_forecast.xlsx', sheet = 'forecast')

# Split data into two groups
selected_traders <- data %>% filter(participant.label %in% c("86T", "04R"))
other_traders <- data %>% filter(!participant.label %in% c("86T", "04R"))

# Define a function to calculate forecast metrics
calculate_forecast_metrics <- function(df) {
  df %>%
    group_by(subsession.round_number) %>%
    summarize(
      avg_f0 = mean(player.f0, na.rm = TRUE),
      avg_f1 = mean(player.f1, na.rm = TRUE),
      avg_f2 = mean(player.f2, na.rm = TRUE),
      avg_f3 = mean(player.f3, na.rm = TRUE),
      avg_forecast_error = mean(player.forecast_error, na.rm = TRUE),
      actual_price = mean(group.price, na.rm = TRUE)  # Add the actual group price
    )
}

# Calculate forecast metrics for each group
forecast_metrics_selected <- calculate_forecast_metrics(selected_traders)
forecast_metrics_others <- calculate_forecast_metrics(other_traders)

# Combine data for plotting
combined_forecast_metrics <- bind_rows(
  mutate(forecast_metrics_selected, group = "Prolific participants"),
  mutate(forecast_metrics_others, group = "Lab participants")
)

# Plotting the results
plot=ggplot(combined_forecast_metrics, aes(x = subsession.round_number)) +
  geom_line(aes(y = avg_f0, color = "Forecast current round")) +
  geom_line(aes(y = avg_f1, color = "Forecast one period ahead")) +
  geom_line(aes(y = avg_f2, color = "Forecast two periods ahead")) +
  geom_line(aes(y = avg_f3, color = "Forecast three periods ahead")) +
  geom_line(aes(y = avg_forecast_error, color = "Forecast Error")) +
  geom_line(aes(y = actual_price, color = "Market price"), size = 1.2, linetype = "solid") + # Ensure market price appears in legend
  scale_color_manual(values = c("Forecast current round" = "blue",
                                "Forecast one period ahead" = "green",
                                "Forecast two periods ahead" = "red",
                                "Forecast three periods ahead" = "purple",
                                "Forecast Error" = "orange",
                                "Market price" = "black")) + # Manually set colors
  facet_wrap(~group) +
  labs(title = "Forecast vs. Actual Price Comparison", x = "Round Number", y = "Value of price forecasts and Market price", color = "Metrics") +
  theme(panel.background = element_rect(fill = "white", colour = "white")) # Set background to white
  theme_minimal()

# Print the results
print(forecast_metrics_selected)
print(forecast_metrics_others)

ggsave(filename = "/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/forecast_comparison_plot_prolific_lab.png", plot = plot, width = 12, height = 8, dpi = 300)



### Risky choices

### Risk by participant
# Define a function to calculate risk choices per trading round for each participant
# Load necessary libraries
library(dplyr)
library(ggplot2)

# Define a function to categorize trading rounds into subperiods
categorize_subperiod <- function(round_number) {
  if (round_number <= 10) {
    "1-10"
  } else if (round_number <= 20) {
    "11-20"
  } else {
    "21-33"
  }
}

# Function to calculate risk choices per subperiod for each participant
calculate_risk_by_subperiod <- function(df) {
  df %>%
    mutate(subperiod = sapply(subsession.round_number, categorize_subperiod)) %>%
    group_by(subperiod, participant.label) %>%
    summarize(count_risk = sum(player.risk, na.rm = TRUE)) %>%
    ungroup() %>%
    filter(count_risk > 0)  # Exclude participants with no risky choices
}

# Apply the function to the data
risk_by_subperiod <- calculate_risk_by_subperiod(data)

# Separate the two specified participants from the rest
risk_selected_participants <- risk_by_subperiod %>% filter(participant.label %in% c("86T", "04R"))
risk_other_participants <- risk_by_subperiod %>% filter(!participant.label %in% c("86T", "04R"))

# Combine data for plotting with an indicator for group
combined_risk_by_subperiod <- bind_rows(
  mutate(risk_other_participants, group = "Lab participants"),
  mutate(risk_selected_participants, group = "Prolific participants")
)

# Get unique participant labels
unique_participants <- unique(combined_risk_by_subperiod$participant.label)

# Define color shades for selected traders
selected_trader_colors <- c("86T" = "dodgerblue3", "04R" = "dodgerblue1")

# Generate grey shades for other traders
n_other_traders <- length(unique_participants) - length(selected_trader_colors)
other_trader_colors <- setNames(gray.colors(n_other_traders), setdiff(unique_participants, names(selected_trader_colors)))

# Combine color vectors
custom_colors <- c(selected_trader_colors, other_trader_colors)

# Plotting the results with custom colors
plot_risk_by_subperiod <- ggplot(combined_risk_by_subperiod, aes(x = subperiod, y = count_risk, fill = participant.label)) +
  geom_bar(stat = "identity", position = position_dodge()) +
  scale_fill_manual(values = custom_colors) +
  scale_y_continuous(breaks = seq(0, max(combined_risk_by_subperiod$count_risk, na.rm = TRUE), by = 1)) +
  facet_grid(group ~ .) +
  labs(title = "Risky Choices per Subperiod by Participant", x = "Subperiod", y = "Count of Risky Choices", fill = "Participant") +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white"),
        plot.background = element_rect(fill = "white", colour = "white"), # Ensure plot background is white
        legend.position = "bottom")

# Save the plot
ggsave(filename = "/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/risky_choices_by_subperiod.png", 
       plot = plot_risk_by_subperiod, 
       width = 12, 
       height = 8, 
       dpi = 300)

# Print the results
print(combined_risk_by_subperiod)
# Print the results
print(combined_risk_by_subperiod)