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

# Pilot 4
data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_01_12/orders_2024-01-12.csv')

# Pilot 3
#data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_03_23_11_30/orders_2023-11-30.csv')

# Pilot 1
#data <- read_csv('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_01_23_11_16/rounds_2023-11-16.csv')


data <- rename(data, round_number=Round)


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
plot1 <- ggplot(data, aes(x = round_number)) +
  geom_line(aes(y = market_price), color = "blue") +
  geom_point(aes(y = market_price), color = "blue") + # Adding marker points to the line
  geom_bar(aes(y = volume/10), stat = "identity", fill = "gray", alpha = 0.5) +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white")) +
  labs(title = "Market Price and Volume per Round",
       x = "Round Number",
       y = "Market Price / Volume")

# 4. Calculate bid-ask spread per round
# Assuming 'price' column has bid prices for 'BUY' type and ask prices for 'SELL' type
bid_ask_spread_per_round <- data %>%
  group_by(round_number) %>%
  summarise(
    bid_price = max(price[type == 'BUY'], na.rm = TRUE),
    ask_price = min(price[type == 'SELL'], na.rm = TRUE),
    spread = ask_price - bid_price
  )

# 3. Plot for Bid-Ask Spread per Round
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


# Viewing the results
print(average_price_per_round)
print(orders_per_round)
print(average_volume_per_round)
print(bid_ask_spread_per_round)




########################
# FORECAST ANALYSIS AND FIGURE

# Load necessary libraries
library(readr)
library(dplyr)
library(ggplot2)

# Read the CSV file (replace 'forecast_data.csv' with your actual file path)

forecast_data <- read_excel('/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/pilot_2024_01_12/rounds_2024-01-12_forecast.xlsx', sheet = 'forecast') # Pilot 4, online only
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
  start_row <- (round - 1) * 6 + 1 # 6 here because there are 6 participants, change accordingly
  end_row <- round * 6
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

# Convert the forecast_matrix to a long format for easier plotting
forecast_long <- melt(as.data.frame(forecast_matrix), id.vars = NULL, variable.name = "Forecast_Period", value.name = "Forecast_Price")
forecast_long$Round <- rep(1:33, times = 4) # Adding a Round column for merging

# Combine market_price from data and forecast data
combined_data <- merge(data, forecast_long, by = "Round", all = TRUE)

# Create the plot
plot3 <- ggplot(combined_data, aes(x = Round)) +
  geom_line(aes(y = market_price, colour = "Market Price"), size = 1) +
  geom_line(aes(y = Forecast_Price, colour = Forecast_Period), size = 1, linetype = "dashed") +
  scale_color_brewer(palette = "Set1", name = "Data Type") +
  theme_minimal() +
  theme(panel.background = element_rect(fill = "white", colour = "white")) +
  labs(title = "Market Price vs Forecast Price",
       x = "Round Number",
       y = "Price")


              

# save plots
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/plot1_pilot4.png", plot1, width = 10, height = 8)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/plot2_pilot4.png", plot2, width = 10, height = 8)
ggsave("/Users/mihai/Desktop/Caltech/Neurofinance/data/piloting/plot3_pilot4.png", plot3, width = 10, height = 8)

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





