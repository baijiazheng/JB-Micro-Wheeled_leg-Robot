/**
 * @file    main.c
 * @brief   驱动板 F103 主程序: 时钟/外设初始化 + 主循环
 *
 * 外设:
 *   TIM1/TIM3: 三相 PWM (L6234)
 *   TIM4:      1kHz 控制中断
 *   I2C1/I2C2: AS5600 编码器
 *   CAN:       与主控板通信
 */

#include "stm32f1xx_hal.h"
#include "../app/control_loop.h"

/* ---- 全局句柄 ---- */
I2C_HandleTypeDef hi2c1;
I2C_HandleTypeDef hi2c2;
CAN_HandleTypeDef  hcan;
TIM_HandleTypeDef  htim4;

/* ---- 姿态占位 (MPU6050 驱动待补) ---- */
float imu_pitch_deg = 0.0f;
float imu_gyro_deg  = 0.0f;

static void SystemClock_Config(void);
static void MX_I2C1_Init(void);
static void MX_I2C2_Init(void);
static void MX_CAN_Init(void);
static void MX_TIM4_Init(void);

int main(void)
{
    HAL_Init();
    SystemClock_Config();

    MX_I2C1_Init();
    MX_I2C2_Init();
    MX_CAN_Init();
    MX_TIM4_Init();

    control_loop_init();
    HAL_TIM_Base_Start_IT(&htim4); /* 启动 1kHz 控制中断 */

    while (1) {
        control_loop_background();
        HAL_Delay(5);
    }
}

/* ================= 时钟: 8MHz HSE -> 72MHz ================= */
static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_ON;
    osc.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
    osc.HSIState = RCC_HSI_ON;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLMUL = RCC_PLL_MUL9;          /* 8MHz ×9 = 72MHz */
    HAL_RCC_OscConfig(&osc);

    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                  | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV2;     /* APB1 = 36MHz */
    clk.APB2CLKDivider = RCC_HCLK_DIV1;     /* APB2 = 72MHz */
    HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_2);
}

/* ================= I2C1: AS5600 #1 (PB6/PB7) ================= */
static void MX_I2C1_Init(void)
{
    hi2c1.Instance = I2C1;
    hi2c1.Init.ClockSpeed = 400000;
    hi2c1.Init.DutyCycle = I2C_DUTYCYCLE_2;
    hi2c1.Init.OwnAddress1 = 0;
    hi2c1.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2 = 0;
    hi2c1.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    HAL_I2C_Init(&hi2c1);
}

/* ================= I2C2: AS5600 #2 + MPU6050 (PB10/PB11) ================= */
static void MX_I2C2_Init(void)
{
    hi2c2.Instance = I2C2;
    hi2c2.Init.ClockSpeed = 400000;
    hi2c2.Init.DutyCycle = I2C_DUTYCYCLE_2;
    hi2c2.Init.OwnAddress1 = 0;
    hi2c2.Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    hi2c2.Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    hi2c2.Init.OwnAddress2 = 0;
    hi2c2.Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    hi2c2.Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    HAL_I2C_Init(&hi2c2);
}

/* ================= CAN: 500kbps (PA11/PA12) ================= */
static void MX_CAN_Init(void)
{
    hcan.Instance = CAN1;
    hcan.Init.Prescaler = 9;         /* APB1 36MHz / 9 / 8 = 500kHz */
    hcan.Init.Mode = CAN_MODE_NORMAL;
    hcan.Init.SyncJumpWidth = CAN_SJW_1TQ;
    hcan.Init.TimeSeg1 = CAN_BS1_5TQ;
    hcan.Init.TimeSeg2 = CAN_BS2_2TQ;
    hcan.Init.TimeTriggeredMode = DISABLE;
    hcan.Init.AutoBusOff = ENABLE;
    hcan.Init.AutoWakeUp = DISABLE;
    hcan.Init.AutoRetransmission = ENABLE;
    hcan.Init.ReceiveFifoLocked = DISABLE;
    hcan.Init.TransmitFifoPriority = DISABLE;
    HAL_CAN_Init(&hcan);
}

/* ================= TIM4: 1kHz 控制中断 ================= */
static void MX_TIM4_Init(void)
{
    __HAL_RCC_TIM4_CLK_ENABLE();
    htim4.Instance = TIM4;
    htim4.Init.Prescaler = 720 - 1;    /* 72MHz / 720 = 100kHz */
    htim4.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim4.Init.Period = 100 - 1;       /* 100kHz / 100 = 1kHz */
    htim4.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim4.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    HAL_TIM_Base_Init(&htim4);
}

/* ================= 1kHz 控制中断回调 ================= */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM4) {
        control_loop_1khz();
    }
}

/* ================= 错误处理 ================= */
void Error_Handler(void)
{
    __disable_irq();
    while (1) { }
}
