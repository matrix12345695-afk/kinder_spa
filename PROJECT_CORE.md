# 🚀 KINDER SPA BOT — CORE ARCHITECTURE

## 📌 Описание проекта

Telegram-бот для записи клиентов в детский SPA-центр.

Основной функционал:
- 📋 Запись на услуги
- 👩‍⚕️ Выбор специалиста
- 📅 Выбор даты и времени
- 📞 Сбор контактных данных
- 📊 Хранение всех данных в Google Sheets

---

## 🧠 Архитектура

Проект построен по модульной структуре:
handlers/
start.py
booking/
start.py
therapist.py
date.py
time.py
contacts.py
my_appointments.py
admin.py

sheets.py
config.py
main.py

---

## 🔌 Основные модули

### 1. `main.py`
- Точка входа
- Подключение роутеров
- Настройка webhook
- Запуск приложения

---

### 2. `sheets.py`
💾 Главный data-layer проекта

Отвечает за:
- Подключение к Google Sheets
- Кэширование данных
- CRUD операции

Основные функции:

#### 📋 Услуги
- `get_active_masses(lang)`

#### 👩‍⚕️ Специалисты
- `get_therapists_for_massage(massage_id)`

#### 📅 Записи
- `create_appointment(...)`
- `get_user_appointments(user_id)`
- `get_all_appointments_full()`
- `update_appointment_status(...)`

#### ⏰ Время
- `get_free_times(...)`

---

### 3. `handlers/booking/`
🔥 Основная бизнес-логика записи

FSM этапы:
1. Выбор услуги
2. Выбор специалиста
3. Выбор даты
4. Выбор времени
5. Имя родителя
6. Имя ребёнка
7. Возраст
8. Телефон

---

## 📊 Структура Google Sheets

### 🧸 masses
| id | name_ru | name_uz | price | duration_min | age_from | age_to | active |

---

### 👩‍⚕️ therapists
| id | name | experience | description |

---

### 🔗 therapist_masses
| therapist_id | massage_id |

---

### 📅 schedule
| therapist_id | weekday |

---

### 📝 appointments
| user_id | massage_id | therapist_id | datetime | parent_name | child_name | child_age | phone | status | created_at |

---

### 👤 users
| user_id | lang |

---

### 🛠 admins
| user_id | role |

---

## ⚡ Особенности

### 🚀 Кэширование
- TTL: 20 секунд
- Ускоряет работу бота
- Снижает нагрузку на Google Sheets

---

### 🧠 FSM (Finite State Machine)
Используется для последовательной записи клиента.

---

### ⚠️ Обработка ошибок
- Все ошибки отправляются оператору в Telegram
- Логи сохраняются в консоль

---

### 📱 UX решения
- Кнопка отправки номера (`request_contact`)
- Автоматическое скрытие клавиатуры
- Красивые карточки услуг и специалистов

---

## 🔐 ENV переменные
BOT_TOKEN=xxx
GOOGLE_CREDENTIALS=xxx
SPREADSHEET_NAME=xxx

---

## 🔮 Дальнейшее развитие

План улучшений:

- 🔔 Напоминания клиентам
- ❌ Отмена записи
- 📊 Админ-панель
- 💰 Учёт доходов
- 📈 Аналитика
- 🧾 История клиента

---

## 🏁 Итог

Это не просто Telegram-бот.

Это:
> 💼 Мини CRM система для бизнеса
> 📅 С автоматической записью
> 📊 С хранением данных
> ⚡ С возможностью масштабирования
