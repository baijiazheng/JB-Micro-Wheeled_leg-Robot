/**
 * @file    main.c
 * @brief   主控板 F407 主程序: 时钟/外设初始化 + 主循环
 *
 * 外设:
 *   USART6: STS3032 舵机总线 (1Mbps, PC6/PC7)
 *   CAN1:   与驱动板通信 (500kbps, PB8/PB9)
 */

#include "stm32f4xx_hal.h"
#include "../app/main_control.h"

UART_HandleTypeDef huart6;
CAN_HandleTypeDef  hcan1;

static void SystemClock_Config(void);
static void MX_USART6_UART_Init(void);
static void MX_CAN1_Init(void);

int main(void)
{
    HAL_Init();
    SystemClock_Config();

    MX_USART6_UART_Init();
    MX_CAN1_Init();

    main_control_init();

    while (1) {
        main_control_loop();
        HAL_Delay(5);
    }
}

/* ============ 时钟: 8MHz HSE -> 168MHz ============ */
static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 8;
    osc.PLL.PLLN = 336;
    osc.PLL.PLLP = RCC_PLLP_DIV2;
    osc.PLL.PLLQ = 7;
    HAL_RCC_OscConfig(&osc);

    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                  | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV4;   /* APB1 = 42MHz */
    clk.APB2CLKDivider = RCC_HCLK_DIV2;   /* APB2 = 84MHz */
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_5);
}

/* ============ USART6: 舵机总线 1Mbps (PC6/PC7) ============ */
static void MX_USART6_UART_Init(void)
{
    __HAL_RCC_USART6_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {0};
    gpio.Pin = GPIO_PIN_6 | GPIO_PIN_7;
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio.Alternate = GPIO_AF8_USART6;
    HAL_GPIO_Init(GPIOC, &gpio);

    huart6.Instance = USART6;
    huart6.Init.BaudRate = 1000000;      /* 1Mbps */
    huart6.Init.WordLength = UART_WORDLENGTH_8B;
    huart6.Init.StopBits = UART_STOPBITS_1;
    huart6.Init.Parity = UART_PARITY_NONE;
    huart6.Init.Mode = UART_MODE_TX_RX;
    huart6.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart6.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart6);
}

/* ============ CAN1: 500kbps (PB8/PB9) ============ */
static void MX_CAN1_Init(void)
{
    __HAL_RCC_CAN1_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {0};
    gpio.Pin = GPIO_PIN_8 | GPIO_PIN_9;
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio.Alternate = GPIO_AF9_CAN1;
    HAL_GPIO_Init(GPIOB, &gpio);

    hcan1.Instance = CAN1;
    hcan1.Init.Prescaler = 7;           /* APB1 42MHz / 7 / 12 = 500kHz */
    hcan1.Init.Mode = CAN_MODE_NORMAL;
    hcan1.Init.SyncJumpWidth = CAN_SJW_1TQ;
    hcan1.Init.TimeSeg1 = CAN_BS1_9TQ;
    hcan1.Init.TimeSeg2 = CAN_BS2_2TQ;
    hcan1.Init.TimeTriggeredMode = DISABLE;
    hcan1.Init.AutoBusOff = ENABLE;
    hcan1.Init.AutoWakeUp = DISABLE;
    hcan1.Init.AutoRetransmission = ENABLE;
    hcan1.Init.ReceiveFifoLocked = DISABLE;
    hcan1.Init.TransmitFifoPriority = DISABLE;
    HAL_CAN_Init(&hcan1);
}

void Error_Handler(void)
{
    __disable_irq();
    while (1) { }
}
