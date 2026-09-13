/**
 * @file    stm32f1xx_it.h
 * @brief   中断处理函数声明
 */

#ifndef STM32F1xx_IT_H
#define STM32F1xx_IT_H

void SysTick_Handler(void);
void TIM4_IRQHandler(void);
void USB_LP_CAN1_RX0_IRQHandler(void);

#endif /* STM32F1xx_IT_H */
