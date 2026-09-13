/**
 * @file    pwm.c
 * @brief   L6234 三相 PWM 驱动实现 (STM32F103 HAL)
 */

#include "pwm.h"
#include "stm32f1xx_hal.h"

#define PWM_FREQ_HZ    20000u   /* 20kHz 开关频率 */
#define PWM_PERIOD     3600u    /* ARR: 72MHz / 20kHz = 3600 */

static TIM_HandleTypeDef htim1;   /* 电机1 */
static TIM_HandleTypeDef htim3;   /* 电机2 */

/* ---- 通用定时器 PWM 初始化 ---- */
static void tim_pwm_init(TIM_HandleTypeDef *htim, TIM_TypeDef *inst)
{
    htim->Instance = inst;
    htim->Init.Prescaler = 0;               /* 不分频, 72MHz */
    htim->Init.Period = PWM_PERIOD - 1;
    htim->Init.CounterMode = TIM_COUNTERMODE_UP;
    htim->Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim->Init.RepetitionCounter = 0;
    htim->Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    HAL_TIM_PWM_Init(htim);
}

/* ---- 配置一个 PWM 通道 ---- */
static void pwm_config_channel(TIM_HandleTypeDef *htim, uint32_t channel)
{
    TIM_OC_InitTypeDef oc = {0};
    oc.OCMode = TIM_OCMODE_PWM1;
    oc.Pulse = 0;
    oc.OCPolarity = TIM_OCPOLARITY_HIGH;
    oc.OCNPolarity = TIM_OCNPOLARITY_HIGH;
    oc.OCFastMode = TIM_OCFAST_DISABLE;
    oc.OCIdleState = TIM_OCIDLESTATE_RESET;
    HAL_TIM_PWM_ConfigChannel(htim, &oc, channel);
}

void pwm_init(void)
{
    /* 时钟 */
    __HAL_RCC_TIM1_CLK_ENABLE();
    __HAL_RCC_TIM3_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();

    /* GPIO: 电机1 PA8/PA9/PA10 (TIM1_CH1/2/3), 电机2 PA6/PA7/PB0 (TIM3_CH1/2/3) */
    GPIO_InitTypeDef gpio = {0};
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Speed = GPIO_SPEED_FREQ_HIGH;

    gpio.Pin = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10;
    HAL_GPIO_Init(GPIOA, &gpio);

    gpio.Pin = GPIO_PIN_6 | GPIO_PIN_7;
    HAL_GPIO_Init(GPIOA, &gpio);

    gpio.Pin = GPIO_PIN_0;
    HAL_GPIO_Init(GPIOB, &gpio);

    /* 定时器 */
    tim_pwm_init(&htim1, TIM1);
    tim_pwm_init(&htim3, TIM3);

    pwm_config_channel(&htim1, TIM_CHANNEL_1);
    pwm_config_channel(&htim1, TIM_CHANNEL_2);
    pwm_config_channel(&htim1, TIM_CHANNEL_3);

    pwm_config_channel(&htim3, TIM_CHANNEL_1);
    pwm_config_channel(&htim3, TIM_CHANNEL_2);
    pwm_config_channel(&htim3, TIM_CHANNEL_3);

    /* 启动 PWM */
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2);
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_3);
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_2);
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_3);
}

/* ---- 占空比 -> 比较值 ---- */
static uint32_t duty_to_ccr(float duty)
{
    if (duty < 0.0f) duty = 0.0f;
    if (duty > 1.0f) duty = 1.0f;
    return (uint32_t)(duty * PWM_PERIOD);
}

void pwm_set_motor1(float duty_a, float duty_b, float duty_c)
{
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, duty_to_ccr(duty_a));
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, duty_to_ccr(duty_b));
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_3, duty_to_ccr(duty_c));
}

void pwm_set_motor2(float duty_a, float duty_b, float duty_c)
{
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, duty_to_ccr(duty_a));
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_2, duty_to_ccr(duty_b));
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_3, duty_to_ccr(duty_c));
}

/* ---- 使能: PB1(电机1) PB12(电机2) ---- */
void pwm_enable(uint8_t en)
{
    GPIO_InitTypeDef gpio = {0};
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    gpio.Pin = GPIO_PIN_1 | GPIO_PIN_12;

    /* PB1 在 GPIOB, PB12 也在 GPIOB */
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1 | GPIO_PIN_12,
                      en ? GPIO_PIN_SET : GPIO_PIN_RESET);
}
