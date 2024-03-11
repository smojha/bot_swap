# Load necessary libraries
library(readxl)
library(dplyr)
library(ggplot2)
library(tidyr)
library(readr)
install.packages("openxlsx")
library(openxlsx)

rm(list=ls())


# Read the Excel file (replace 'your_file.xlsx' with your actual file path)
# Hybrid data 07 March 2024
data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/actual markets/03_07_2024_hybrid/orders_2024-03-07.csv')


# Online pilot (pilot 5)
#data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/orders_2024-02-20.csv')

data_unique <- data %>%
  distinct(round_number, volume, .keep_all = TRUE)
# Pilot 4
#data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_01_12/orders_2024-01-12.csv')
# Pilot 3
#data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/orders_2023-11-30.csv')
# Pilot 1
#data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_01_23_11_16/rounds_2023-11-16.csv')


#data <- rename(data, period=Round)


# 1. Calculate average price per round
average_price_per_round <- data %>%
  group_by(round_number) %>%
  summarise(average_price = sum(price * quantity) / sum(quantity))

# 1. Line Graph for Average Market Price per Round
ggplot(data, aes(x = round_number, y = market_price)) +
  geom_line() +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white")) +
  labs(title = "Average Market Price per Round",
       x = "Round Number",
       y = "Average Market Price")

# 2. Count BUY and SELL orders per round
orders_per_round <- data %>%
  group_by(round_number, type) %>%
  summarise(order_count = n()) %>%
  pivot_wider(names_from = type, values_from = order_count, values_fill = list(order_count = 0))

# 3. Calculate average volume per round
average_volume_per_round <- data %>%
  group_by(round_number) %>%
  summarise(average_volume = mean(volume))

# 1. Line Graph for Average Market Price per Round with Blue Line and Round Markers
ggplot(data, aes(x = round_number, y = market_price)) +
  geom_line(color = "blue") +
  geom_point(shape = 21, fill = "blue") +
  theme_minimal() +
  labs(title = "Average Market Price per Round",
       x = "Round Number",
       y = "Average Market Price")


# 2. Combined Graph for Market Price (Line) and Volume (Bar)
# Remove duplicate entries for each round based on round_number for volume
# Plot for Market Price
market_price_plot <- ggplot(data, aes(x = round_number)) +
  geom_line(aes(y = market_price), color = "blue") +
  geom_point(aes(y = market_price), color = "blue") +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white")) +
  labs(title = "Market Price per Round", x = "Round Number", y = "Market Price")

# Plot for Volume (already provided in your question)
volume_plot <- ggplot(data_unique, aes(x = round_number, y = volume)) +
  geom_bar(stat = "identity", fill = "grey", alpha = 0.5) +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white")) +
  labs(title = "Volume per Round", x = "Round Number", y = "Volume")

# Combine the plots using patchwork
market_volume_plot <- market_price_plot / volume_plot 

# Display the combined plot
print(market_volume_plot)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/forecast/hybrid_03072024/market_price_volume.png", market_volume_plot, width = 12, height = 8, dpi = 300)

# 4. Calculate bid-ask spread per round
# Assuming 'price' column has bid prices for 'BUY' type and ask prices for 'SELL' type
bid_ask_spread_per_round <- data %>%
  group_by(round_number) %>%
  summarise(
    bid_price = max(price[type == 'BUY'], na.rm = TRUE),
    ask_price = min(price[type == 'SELL'], na.rm = TRUE),
    spread = ask_price - bid_price
  )


# 5. Plot for Bid-Ask Spread per Round
# Assuming 'bid_ask_spread_per_round' is calculated as in the previous step
plot2 <- ggplot(bid_ask_spread_per_round, aes(x = round_number)) +
  geom_segment(aes(xend = round_number, y = bid_price, yend = ask_price), color = "red") +
  geom_line(data = data, aes(y = market_price), color = "blue") + # Overlaying market price
  geom_point(data = data, aes(y = market_price), color = "blue") + # Adding marker points to market price
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white")) +
  labs(title = "Bid-Ask Spread and Market Price per Round",
       x = "Round Number",
       y = "Price")
plot2

# Calculate average bid ask spread
avg_bid_ask_spread_per_round <- data %>%
  group_by(round_number) %>%
  summarise(
    bid_price = mean(price[type == 'BUY'], na.rm = TRUE),
    ask_price = mean(price[type == 'SELL'], na.rm = TRUE),
    avg_spread = ask_price - bid_price
  )

# Assuming 'bid_ask_spread_per_round' is calculated as in the previous step
plot_avg_spread <- ggplot(avg_bid_ask_spread_per_round, aes(x = round_number)) +
  geom_segment(aes(xend = round_number, y = bid_price, yend = ask_price), color = "red") +
  geom_line(data = data, aes(y = market_price), color = "blue") + # Overlaying market price
  geom_point(data = data, aes(y = market_price), color = "blue") + # Adding marker points to market price
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white")) +
  labs(title = "Bid-Ask Spread and Market Price per Round",
       x = "Round Number",
       y = "Price")

plot_avg_spread


# 2. Plot for Market Price and Bid-Ask Spread
market_price_bid_ask_plot <- ggplot(data, aes(x = round_number)) +
  geom_line(aes(y = market_price), color = "blue") +
  geom_point(aes(y = market_price), color = "blue") +
  geom_segment(data = bid_ask_spread_per_round, aes(xend = round_number, y = bid_price, yend = ask_price), color = "red") +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white")) +
  labs(title = "Market Price and Bid-Ask Spread per Round",
       x = "Round Number",
       y = "Price")

market_price_bid_ask_plot



# Now plot the volume for each trading round using the deduplicated data
volume_plot <- ggplot(data_unique, aes(x = round_number, y = volume)) +
  geom_bar(stat = "identity", fill = "grey", alpha = 0.5) +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white")) +
  labs(x = "Round Number", y = "Volume")

# Display the plot
print(volume_plot)

# Combine the plots
final_plot <- market_price_bid_ask_plot / volume_plot 

# Display the combined plot
final_plot

# Save the plot
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/figures/forecast/hybrid_03072024/market_price_volume_liquidity.png", final_plot, width = 12, height = 8, dpi = 300)
#ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/plot2_pilot4.png", plot2, width = 10, height = 8)

# Viewing the results
print(average_price_per_round)
print(orders_per_round)
print(average_volume_per_round)
print(bid_ask_spread_per_round)


########################
# RISK ANALYSIS AND FIGURE
library(readxl)
library(dplyr)
library(ggplot2)
library(patchwork)

# Read the data
orders <- read_csv("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/orders_2024-02-20.csv")
rounds <- read_csv("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/rounds_2024-02-20.csv")

# Process the data
rounds_summary <- rounds %>%
  group_by(subsession.round_number) %>%
  summarize(
    mean_r = mean(player.dose_r, na.rm = TRUE),
    mean_mu = mean(player.dose_mu, na.rm = TRUE)
  ) %>%
  ungroup()

market_trend <- orders %>%
  select(round_number, price) %>%
  group_by(round_number) %>%
  summarize(group_mean_price = mean(price, na.rm = TRUE))

plot_data <- merge(x = rounds_summary, y = market_trend, by.x = "subsession.round_number", by.y = "round_number", all = TRUE)

# Adjust plot_data for faceting
plot_data_long <- plot_data %>%
  pivot_longer(cols = c(mean_r, mean_mu), names_to = "variable", values_to = "value")

# Create the combined plot
p <- ggplot() +
  # Price plot
  geom_line(data = plot_data, aes(x = subsession.round_number, y = group_mean_price, group = 1),
            color = "black", size = 1, linetype = "solid") +
  geom_point(data = plot_data, aes(x = subsession.round_number, y = group_mean_price), 
             color = "black", size = 2, shape = 1) +
  # R and Mu plot using facets
  geom_col(data = plot_data_long, aes(x = subsession.round_number, y = value, fill = variable), show.legend = FALSE) +
  scale_fill_manual(values = c("mean_r" = "red", "mean_mu" = "blue")) +
  facet_grid(variable ~ ., scales = "free_y", space = "free_y") +
  labs(y = "Value", x = "Round Number") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        strip.background = element_blank(),
        strip.text.x = element_text(size = 0))

# Print the combined plot
print(p)

########################
# FORECAST ANALYSIS AND FIGURE

# Load necessary libraries
library(readr)
library(dplyr)
library(ggplot2)

# Read the CSV file (replace 'forecast_data.csv' with your actual file path)

forecast_data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_02_20_online/rounds_2024-02-20.csv') # Pilot 5, online only
#forecast_data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_01_12/rounds_2024-01-12_forecast.xlsx', sheet = 'forecast') # Pilot 4, online only
#forecast_data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/rounds_2023-11-30_forecast.xlsx', sheet = 'forecast') # Pilot 3
#forecast_data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_01_23_11_16/rounds_2023-11-16_forecast.xlsx', sheet = 'forecast') # Pilot 1

# Function to replace NA with row average or a non-NA value
replace_na_with_row_avg <- function(x) {
  if (all(is.na(x))) {
    return(x)
  }
  na_count <- sum(is.na(x))
  if (na_count > 0 && na_count < length(x)) {
    row_avg <- mean(x, na.rm = TRUE)
    x[is.na(x)] <- row_avg
  }
  return(x)
}

shift_matrix_column <- function(matrix, column_index, shift_by) {
  if (shift_by > 0) {
    # Create a vector of NA values to add at the beginning of the column
    na_pad <- rep(NA, shift_by)
    # Shift the column down by the specified amount, adding NA values at the start
    matrix[, column_index] <- c(na_pad, matrix[1:(nrow(matrix) - shift_by), column_index])
  }
  return(matrix)
}

# Apply the function to your forecast_data
forecast_data <- forecast_data %>%
  mutate(across(starts_with("player.f"), replace_na_with_row_avg))

# Replace entirely empty rows with values from the previous round
forecast_data <- forecast_data %>%
  fill(starts_with("player.f"), .direction = "down")

# Create an empty 33x4 matrix for the forecast
forecast_matrix <- matrix(NA, nrow = 33, ncol = 4)
colnames(forecast_matrix) <- paste("Forecast for Period", 0:3)

# Calculate the averages and fill the matrix
for (round in 1:33) {
  start_row <- (round - 1) * 18 + 1 # 6 here because there are 6 participants, change accordingly
  end_row <- round * 18
  for (period in 1:4) {
    column_name <- paste("player.f", period - 1, sep = "")
    # Extract data as a numeric vector
    forecast_values <- as.numeric(forecast_data[[column_name]][start_row:end_row])
    # Calculate the mean, if the conversion was successful
    if (!all(is.na(forecast_values))) {
      forecast_matrix[round, period] <- mean(forecast_values, na.rm = TRUE)
    }
  }
}


# Check the forecast_matrix
forecast_matrix

library(reshape2)

# Assuming forecast_matrix is your matrix and market_data is your dataframe with actual market prices
forecast_df <- as.data.frame(forecast_matrix)
forecast_df$Round <- 1:33
forecast_long <- melt(forecast_df, id.vars = "Round", variable.name = "Forecast_Period", value.name = "Forecast_Price")

# Rename 'round_number' to 'Round' in 'data'
data <- rename(data, Round = round_number)


# Apply the shifting function to the forecast_matrix for the specified columns
forecast_matrix <- shift_matrix_column(forecast_matrix, 2, 1) # Shift column 2 down by 1 row
forecast_matrix <- shift_matrix_column(forecast_matrix, 3, 4) # Shift column 3 down by 4 rows
forecast_matrix <- shift_matrix_column(forecast_matrix, 4, 9) # Shift column 4 down by 9 rows

# Convert the adjusted forecast_matrix to a long format for plotting
forecast_df <- as.data.frame(forecast_matrix)
forecast_df$Round <- 1:nrow(forecast_matrix)
forecast_long <- melt(forecast_df, id.vars = "Round", variable.name = "Forecast_Period", value.name = "Forecast_Price")

# Combine market_price from data and forecast data
combined_data <- merge(data, forecast_long, by = "Round", all = TRUE)

# Proceed with plotting
plot3 <- ggplot(combined_data, aes(x = Round)) +
  geom_line(aes(y = market_price), colour = "black", size = 1) + # Market Price in black
  geom_line(aes(y = Forecast_Price, colour = Forecast_Period), size = 1, linetype = "dashed") +
  scale_color_brewer(palette = "Set1", name = "Data Type", 
                     labels = c("Forecast for period 0", "Forecast for period 2", "Forecast for period 5", "Forecast for period 10")) + # Custom labels
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white"),
        legend.position = "bottom", # Move legend to bottom
        text = element_text(size = 12), # Increase font size for all text
        legend.title = element_text(size = 14), # Increase font size for legend title
        legend.text = element_text(size = 12) # Increase font size for legend items
  ) +
  labs(title = "Market Price vs Forecast Price",
       x = "Round Number",
       y = "Price")

plot3


# save plots
#ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/plot1_pilot4.png", plot1, width = 10, height = 8)
#ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/plot2_pilot4.png", plot2, width = 10, height = 8)
#ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/plot3_pilot4.png", plot3, width = 10, height = 8)

# Save files:
# Create a new workbook
wb <- createWorkbook()

# Add sheets with data
addWorksheet(wb, "Average Price Per Round")
writeData(wb, "Average Price Per Round", average_price_per_round)

addWorksheet(wb, "Orders Per Round")
writeData(wb, "Orders Per Round", orders_per_round)

addWorksheet(wb, "Average Volume Per Round")
writeData(wb, "Average Volume Per Round", average_volume_per_round)

addWorksheet(wb, "Bid-Ask Spread Per Round")
writeData(wb, "Bid-Ask Spread Per Round", bid_ask_spread_per_round)

# Add a sheet with the forecast data
addWorksheet(wb, "Forecast Data")
writeData(wb, "Forecast Data", forecast_df)

# Save the workbook
saveWorkbook(wb, "/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/Pilot1.xlsx", overwrite = TRUE)
saveWorkbook(wb, "/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/Pilot3.xlsx", overwrite = TRUE)





