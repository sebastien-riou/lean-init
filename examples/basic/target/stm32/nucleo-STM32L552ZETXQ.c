
#define STM32L552xx
#include <stm32l5xx.h>

//defines needed by nucleo-common.h
#define NUCLEO_USART USART3
#define SYSTEM_CLOCK_MHZ 4

#define TXD_PIN                      GPIO_BSRR_BS8 /*!< Select pin 8 */
#define RXD_PIN                      GPIO_BSRR_BS9 /*!< Select pin 9 */
#define GPIOD_USART3 7
#define NUCLEO_UART_GPIO GPIOD
#define NUCLEO_UART_GPIO_AF GPIOD_USART3

/** @defgroup FLASH_Private_Constants FLASH Private Constants
  * @{
  */
#define FLASH_BANK_SIZE          (FLASH_SIZE >> 1)
#define FLASH_PAGE_SIZE          0x00000800U

#define FLASH_WRITE_SIZE 8

#include "nucleo-common.h"

//LL specific to that nucleo board
static void LL_AHB2_GRP1_EnableClock(uint32_t Periphs){
  __IO uint32_t tmpreg;
  SET_BIT(RCC->AHB2ENR, Periphs);
  /* Delay after an RCC peripheral clock enabling */
  tmpreg = READ_BIT(RCC->AHB2ENR, Periphs);
  (void)tmpreg;
}

/**
  * @brief  Enable APB1 peripherals clock.
  * @rmtoll APB1ENR1     TIM2EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     TIM3EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     TIM4EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     TIM5EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     TIM6EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     TIM7EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     RTCAPBEN      LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     WWDGEN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     SPI2EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     SPI3EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     USART2EN      LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     USART3EN      LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     UART4EN       LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     UART5EN       LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     I2C1EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     I2C2EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     I2C3EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     CRSEN         LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     PWREN         LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     DAC1EN        LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     OPAMPEN       LL_APB1_GRP1_EnableClock\n
  *         APB1ENR1     LPTIM1EN      LL_APB1_GRP1_EnableClock
  * @param  Periphs This parameter can be a combination of the following values:
  *         @arg @ref LL_APB1_GRP1_PERIPH_ALL
  *         @arg @ref LL_APB1_GRP1_PERIPH_TIM2
  *         @arg @ref LL_APB1_GRP1_PERIPH_TIM3
  *         @arg @ref LL_APB1_GRP1_PERIPH_TIM4
  *         @arg @ref LL_APB1_GRP1_PERIPH_TIM5
  *         @arg @ref LL_APB1_GRP1_PERIPH_TIM6
  *         @arg @ref LL_APB1_GRP1_PERIPH_TIM7
  *         @arg @ref LL_APB1_GRP1_PERIPH_RTCAPB
  *         @arg @ref LL_APB1_GRP1_PERIPH_WWDG
  *         @arg @ref LL_APB1_GRP1_PERIPH_SPI2
  *         @arg @ref LL_APB1_GRP1_PERIPH_SPI3
  *         @arg @ref LL_APB1_GRP1_PERIPH_USART2
  *         @arg @ref LL_APB1_GRP1_PERIPH_USART3
  *         @arg @ref LL_APB1_GRP1_PERIPH_UART4
  *         @arg @ref LL_APB1_GRP1_PERIPH_UART5
  *         @arg @ref LL_APB1_GRP1_PERIPH_I2C1
  *         @arg @ref LL_APB1_GRP1_PERIPH_I2C2
  *         @arg @ref LL_APB1_GRP1_PERIPH_I2C3
  *         @arg @ref LL_APB1_GRP1_PERIPH_CRS
  *         @arg @ref LL_APB1_GRP1_PERIPH_PWR
  *         @arg @ref LL_APB1_GRP1_PERIPH_DAC1
  *         @arg @ref LL_APB1_GRP1_PERIPH_OPAMP
  *         @arg @ref LL_APB1_GRP1_PERIPH_LPTIM1
  * @retval None
  */
static void LL_APB1_GRP1_EnableClock(uint32_t Periphs)
{
  __IO uint32_t tmpreg;
  SET_BIT(RCC->APB1ENR1, Periphs);
  /* Delay after an RCC peripheral clock enabling */
  tmpreg = READ_BIT(RCC->APB1ENR1, Periphs);
  (void)tmpreg;
}


/** @defgroup RCC_LL_EC_USART_CLKSOURCE  Peripheral USARTx clock source selection
  * @{
  */
#define LL_RCC_USART1_CLKSOURCE_PCLK2      (RCC_CCIPR1_USART1SEL << 16U)                           /*!< PCLK2 clock used as USART1 clock source */
#define LL_RCC_USART1_CLKSOURCE_SYSCLK     ((RCC_CCIPR1_USART1SEL << 16U) | RCC_CCIPR1_USART1SEL_0) /*!< SYSCLK clock used as USART1 clock source */
#define LL_RCC_USART1_CLKSOURCE_HSI        ((RCC_CCIPR1_USART1SEL << 16U) | RCC_CCIPR1_USART1SEL_1) /*!< HSI clock used as USART1 clock source */
#define LL_RCC_USART1_CLKSOURCE_LSE        ((RCC_CCIPR1_USART1SEL << 16U) | RCC_CCIPR1_USART1SEL)   /*!< LSE clock used as USART1 clock source */
#define LL_RCC_USART2_CLKSOURCE_PCLK1      (RCC_CCIPR1_USART2SEL << 16U)                           /*!< PCLK1 clock used as USART2 clock source */
#define LL_RCC_USART2_CLKSOURCE_SYSCLK     ((RCC_CCIPR1_USART2SEL << 16U) | RCC_CCIPR1_USART2SEL_0) /*!< SYSCLK clock used as USART2 clock source */
#define LL_RCC_USART2_CLKSOURCE_HSI        ((RCC_CCIPR1_USART2SEL << 16U) | RCC_CCIPR1_USART2SEL_1) /*!< HSI clock used as USART2 clock source */
#define LL_RCC_USART2_CLKSOURCE_LSE        ((RCC_CCIPR1_USART2SEL << 16U) | RCC_CCIPR1_USART2SEL)   /*!< LSE clock used as USART2 clock source */
#define LL_RCC_USART3_CLKSOURCE_PCLK1      (RCC_CCIPR1_USART3SEL << 16U)                           /*!< PCLK1 clock used as USART3 clock source */
#define LL_RCC_USART3_CLKSOURCE_SYSCLK     ((RCC_CCIPR1_USART3SEL << 16U) | RCC_CCIPR1_USART3SEL_0) /*!< SYSCLK clock used as USART3 clock source */
#define LL_RCC_USART3_CLKSOURCE_HSI        ((RCC_CCIPR1_USART3SEL << 16U) | RCC_CCIPR1_USART3SEL_1) /*!< HSI clock used as USART3 clock source */
#define LL_RCC_USART3_CLKSOURCE_LSE        ((RCC_CCIPR1_USART3SEL << 16U) | RCC_CCIPR1_USART3SEL)   /*!< LSE clock used as USART3 clock source */

static void LL_RCC_SetUSARTClockSource(uint32_t USARTxSource){
  MODIFY_REG(RCC->CCIPR1, (USARTxSource >> 16U), (USARTxSource & 0x0000FFFFU));
}

//Our application level HAL
void init(){
  //set flash in dual bank mode 
  SET_BIT(FLASH->OPTR, FLASH_OPTR_DBANK);

  //enable clock for GPIOC (LED, button)
  LL_AHB2_GRP1_EnableClock(RCC_AHB2ENR_GPIOCEN);
  //enable LED pin as output
  LL_GPIO_SetPinMode(LED1_GPIO_Port, LED1_Pin, LL_GPIO_MODE_OUTPUT);
  //enable button pin as input
  LL_GPIO_SetPinMode(USER_BUTTON_GPIO_Port, USER_BUTTON_Pin, LL_GPIO_MODE_INPUT);

  //select clock source for USART3
  LL_RCC_SetUSARTClockSource(LL_RCC_USART3_CLKSOURCE_PCLK1);
  //enable USART3 clock
  LL_APB1_GRP1_EnableClock(RCC_APB1ENR1_USART3EN);
  //enable clock for GPIOD (UART3)
  LL_AHB2_GRP1_EnableClock(RCC_AHB2ENR_GPIODEN);
  
  set_gpio_as_uart();
  set_uart_config();
 }

static void nvm_ll_erase_page(uint64_t*page_addr){
  const uintptr_t bank_addr = (uintptr_t)NVM_BANK_BASE(page_addr);
  const uint32_t bank = (bank_addr - FLASH_BASE_NS)/FLASH_BANK_SIZE;
  const uint32_t page = ((uintptr_t)page_addr - bank_addr)/FLASH_PAGE_SIZE;
  
  //select the bank
  WRITE_BIT(FLASH_NS->NSCR, FLASH_NSCR_NSBKER,bank);

  //select the page
  MODIFY_REG(FLASH_NS->NSCR, (FLASH_NSCR_NSPNB | FLASH_NSCR_NSPER), ((page << FLASH_NSCR_NSPNB_Pos) | FLASH_NSCR_NSPER));
  
  //erase the page
  SET_BIT(FLASH_NS->NSCR, FLASH_NSCR_NSSTRT);

  //wait end of operation
  while(READ_BIT(FLASH_NS->NSSR, FLASH_NSSR_NSBSY));
  WRITE_REG(FLASH_NS->NSCR, 0);//clear NSCR
}

static void nvm_ll_write(uint64_t*dst, const uint64_t*const buf, uint32_t n_words32){
  uint32_t*dst32 = (uint32_t*)dst;
  const uint32_t*const buf32 = (const uint32_t*const)buf;
  WRITE_REG(FLASH_NS->NSCR, FLASH_NSCR_NSPG);
  for(unsigned int i=0;i<n_words32;i+=2){
    dst32[i] = buf32[i];
    __ISB();// Barrier to ensure programming is performed in the right order
    dst32[i+1] = buf32[i+1];

    //wait end of operation
    while(READ_BIT(FLASH_NS->NSSR, FLASH_NSSR_NSBSY));
  }
  WRITE_REG(FLASH_NS->NSCR, 0);//clear NSPG
}

static void nvm_ll_write_page(uint64_t*page_addr, const uint64_t*const buf){
  nvm_ll_write(page_addr, buf, NVM_PAGE_SIZE32);
}

static void nvm_write_page(uint64_t*page_addr, const uint64_t*const buf){
  //erase the page
  nvm_ll_erase_page(page_addr);
  //write
  nvm_ll_write_page(page_addr, buf);
}

static void nvm_update_page(uint64_t*nvm_addr, const uint64_t*const buf, uint32_t size){
  //save whole page in RAM
  uint64_t*page_base = NVM_PAGE_BASE(nvm_addr);
  uint64_t page_buffer[SIZE64(FLASH_PAGE_SIZE)];
  nvm_read64(page_base, page_buffer, FLASH_PAGE_SIZE);

  //update the page in RAM
  uintptr_t offset = ((uintptr_t)nvm_addr - (uintptr_t)page_base)/sizeof(uint64_t);
  for(unsigned int i=0;i<size/sizeof(uint64_t);i++){
    page_buffer[offset+i] = buf[i];
  }

  //write the page in NVM
  nvm_write_page(page_base,page_buffer);
}

//return 0 if success
bool nvm_write64(uint64_t*nvm_addr, const uint64_t*const buf, uint32_t size){
  if(0 == size) return 0;
  /* Disable interrupts to avoid any interruption */
  uint32_t primask_bit = __get_PRIMASK();
  __disable_irq();
  //unlock flash write
  WRITE_REG(FLASH->NSKEYR, FLASH_KEY1);
  WRITE_REG(FLASH->NSKEYR, FLASH_KEY2);

  uint64_t*dst = nvm_addr;
  const uint64_t*src = buf;
  uint32_t remaining = size;

  while(remaining){
    uint32_t size_in_page = NVM_SIZE_IN_PAGE(dst);
    if(remaining<size_in_page) size_in_page = remaining;
    nvm_update_page(dst,src,size_in_page);
    dst += size_in_page / sizeof(uint64_t);
    src += size_in_page / sizeof(uint64_t);
    remaining -= size_in_page;
  }

  //lock flash write
  SET_BIT(FLASH->NSCR, FLASH_NSCR_NSLOCK);

  bool fail = 0;
  for(unsigned int i=0;i<size/sizeof(uint64_t);i++){
    fail |= nvm_addr[i] != buf[i];
  }
  /* Restore interrupts enable bit */
  __set_PRIMASK(primask_bit);

  return fail;
}


uint8_t nvm_erase(void*base_address, unsigned int n_pages){
  if(0 == n_pages) return 0;
  const uintptr_t size = n_pages * FLASH_PAGE_SIZE;
  if(base_address < (void*)&nvm) return 1;
  if(((uintptr_t)base_address + size) > ((uintptr_t)&nvm + sizeof(nvm))) return 2;
  if(0 != ((uintptr_t)base_address % FLASH_PAGE_SIZE)) return 3;
  /* Disable interrupts to avoid any interruption */
  uint32_t primask_bit = __get_PRIMASK();
  __disable_irq();
  //unlock flash write
  WRITE_REG(FLASH->NSKEYR, FLASH_KEY1);
  WRITE_REG(FLASH->NSKEYR, FLASH_KEY2);

  uint64_t*dst64 = (uint64_t*)base_address;
  for(unsigned int i=0;i<n_pages;i++){
    nvm_ll_erase_page(dst64);
    dst64 += SIZE64(FLASH_PAGE_SIZE);
  }

  //lock flash write
  SET_BIT(FLASH->NSCR, FLASH_NSCR_NSLOCK);
  /* Restore interrupts enable bit */
  __set_PRIMASK(primask_bit);
  return 0;
}

uint8_t nvm_write(void*dst_nvm_addr, const void*const src, uintptr_t size){
  if(0 == size) return 0;
  if(dst_nvm_addr < (void*)&nvm) return 1;
  if(((uintptr_t)dst_nvm_addr + size) > ((uintptr_t)&nvm + sizeof(nvm))) return 2;
  if(0 != ((uintptr_t)dst_nvm_addr % FLASH_WRITE_SIZE)) return 3;
  if(0 != (size % FLASH_WRITE_SIZE)) return 4;
  /* Disable interrupts to avoid any interruption */
  uint32_t primask_bit = __get_PRIMASK();
  __disable_irq();
  //unlock flash write
  WRITE_REG(FLASH->NSKEYR, FLASH_KEY1);
  WRITE_REG(FLASH->NSKEYR, FLASH_KEY2);
  uint64_t*dst_nvm_addr64 = (uint64_t*)dst_nvm_addr;
  uint64_t*src64 = (uint64_t*)src;
  
  nvm_ll_write(dst_nvm_addr64, src64, size / sizeof(uint32_t));

  //lock flash write
  SET_BIT(FLASH->NSCR, FLASH_NSCR_NSLOCK);

  bool fail = 0;
  for(unsigned int i=0;i<size/sizeof(uint64_t);i++){
    fail |= dst_nvm_addr64[i] != src64[i];
  }
  /* Restore interrupts enable bit */
  __set_PRIMASK(primask_bit);

  return fail;
}

