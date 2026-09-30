#include "ar01_board_app.h"

#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#include "main.h"
#include "ar01_service.h"

extern ADC_HandleTypeDef hadc1;
extern ADC_HandleTypeDef hadc2;
extern IWDG_HandleTypeDef hiwdg;
extern UART_HandleTypeDef hlpuart1;
extern TIM_HandleTypeDef htim1;
extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim4;
extern TIM_HandleTypeDef htim6;

/* P2.0 MCU-only image. Configuration zeros deliberately make ARM impossible.
 * Direction pins and PWM pins remain GPIO LOW; no motor drive is permitted. */
static const ar01_config_t bench_locked_config = {0};
static ar01_service_t service;
static uint8_t rx_byte;
static uint8_t tx_wire[AR01_MAX_WIRE];
static volatile bool tx_busy;
static uint8_t rx_ring[256];
static volatile uint8_t rx_head;
static volatile uint8_t rx_tail;
static volatile uint32_t timer_ticks;
static uint32_t consumed_ticks;

static void force_drive_low(void)
{
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_8 | GPIO_PIN_9, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_6 | GPIO_PIN_7 |
                             GPIO_PIN_8 | GPIO_PIN_9, GPIO_PIN_RESET);
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, 0);
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, 0);
}

static ar01_inputs_t sample(void *context)
{
    ar01_inputs_t inputs = {0};
    (void)context;
    inputs.left_counter = __HAL_TIM_GET_COUNTER(&htim2);
    inputs.right_counter = (uint16_t)__HAL_TIM_GET_COUNTER(&htim4);
    inputs.left_current_ma = UINT16_MAX;
    inputs.right_current_ma = UINT16_MAX;
    /* ADC scaling, DIAG polarity and E-stop wiring are not bench-validated. */
    inputs.bus_mv = 0;
    inputs.estop_closed = false;
    inputs.left_diag_ok = false;
    inputs.right_diag_ok = false;
    return inputs;
}

static void apply_pwm(void *context, int32_t left, int32_t right)
{
    (void)context;
    (void)left;
    (void)right;
    force_drive_low();
}

static bool transmit(void *context, const uint8_t *bytes, uint16_t length)
{
    (void)context;
    if (tx_busy || length > sizeof(tx_wire)) return false;
    memcpy(tx_wire, bytes, length);
    tx_busy = true;
    if (HAL_UART_Transmit_IT(&hlpuart1, tx_wire, length) != HAL_OK) {
        tx_busy = false;
        return false;
    }
    return true;
}

static void watchdog_refresh(void *context)
{
    (void)context;
    (void)HAL_IWDG_Refresh(&hiwdg);
}

void ar01_board_app_init(void)
{
    GPIO_InitTypeDef gpio = {0};
    bool watchdog_reset = __HAL_RCC_GET_FLAG(RCC_FLAG_IWDGRST) != RESET;
    const ar01_port_t port = {
        .context = NULL,
        .sample = sample,
        .apply_pwm = apply_pwm,
        .transmit = transmit,
        .watchdog_refresh = watchdog_refresh,
    };

    /* Reclaim PWM alternate-function pins as driven-low GPIO for this image.
     * At reset they are high impedance: external pulldowns remain mandatory. */
    force_drive_low();
    gpio.Pin = GPIO_PIN_8 | GPIO_PIN_9;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &gpio);
    force_drive_low();

    if (!ar01_service_init(&service, &bench_locked_config, &port) ||
        HAL_TIM_Encoder_Start(&htim2, TIM_CHANNEL_ALL) != HAL_OK ||
        HAL_TIM_Encoder_Start(&htim4, TIM_CHANNEL_ALL) != HAL_OK)
        Error_Handler();
    if (watchdog_reset) service.core.faults |= AR01_WATCHDOG_RESET;
    __HAL_RCC_CLEAR_RESET_FLAGS();

    HAL_NVIC_SetPriority(TIM6_DAC_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(TIM6_DAC_IRQn);
    HAL_NVIC_SetPriority(LPUART1_IRQn, 6, 0);
    HAL_NVIC_EnableIRQ(LPUART1_IRQn);
    if (HAL_UART_Receive_IT(&hlpuart1, &rx_byte, 1) != HAL_OK ||
        HAL_TIM_Base_Start_IT(&htim6) != HAL_OK)
        Error_Handler();
}

void ar01_board_app_run(void)
{
    while (rx_tail != rx_head) {
        uint8_t value = rx_ring[rx_tail++];
        ar01_service_receive_byte(&service, value, HAL_GetTick());
    }
    if (consumed_ticks != timer_ticks) {
        uint32_t now = timer_ticks;
        if (now - consumed_ticks > 1u)
            service.core.faults |= AR01_CONTROL_OVERRUN;
        consumed_ticks = now;
        ar01_service_tick(&service, HAL_GetTick());
    }
}

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM6) ++timer_ticks;
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance != LPUART1) return;
    uint8_t next = (uint8_t)(rx_head + 1u);
    if (next != rx_tail) {
        rx_ring[rx_head] = rx_byte;
        rx_head = next;
    }
    (void)HAL_UART_Receive_IT(&hlpuart1, &rx_byte, 1);
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == LPUART1) tx_busy = false;
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == LPUART1)
        (void)HAL_UART_Receive_IT(&hlpuart1, &rx_byte, 1);
}

void TIM6_DAC_IRQHandler(void)
{
    HAL_TIM_IRQHandler(&htim6);
}

void LPUART1_IRQHandler(void)
{
    HAL_UART_IRQHandler(&hlpuart1);
}
