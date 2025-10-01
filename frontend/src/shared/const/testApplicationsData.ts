export interface IApplication {
  applicationNumber: number;
  applicationDate: string;
  contactPerson: string;
  city: string;
  applicationStatus: string;
}

export const applicationsData: IApplication[] = [
  {
    applicationNumber: 12561,
    applicationDate: "01.03.2025",
    contactPerson: "Фтодосьев Игорь Романович",
    city: "Пятигорск",
    applicationStatus: "Завершена",
  },
  {
    applicationNumber: 12562,
    applicationDate: "02.03.2025",
    contactPerson: "Киреев Фёдор Романович",
    city: "Москва",
    applicationStatus: "Ожидает",
  },
  {
    applicationNumber: 12563,
    applicationDate: "03.03.2025",
    contactPerson: "Мальцева Ева Данииловна",
    city: "Санкт-Петербург",
    applicationStatus: "Ожидает",
  },
  {
    applicationNumber: 12564,
    applicationDate: "04.03.2025",
    contactPerson: "Рябова Амелия Сергеевна",
    city: "Москва",
    applicationStatus: "В обработке",
  },
  {
    applicationNumber: 12565,
    applicationDate: "05.03.2025",
    contactPerson: "Зубков Андрей Артёмович",
    city: "Коломна",
    applicationStatus: "Завершена",
  },
  {
    applicationNumber: 12566,
    applicationDate: "06.03.2025",
    contactPerson: "Константинова Ева Данииловна",
    city: "Санкт-Петербург",
    applicationStatus: "В обработке",
  },
  {
    applicationNumber: 12567,
    applicationDate: "07.03.2025",
    contactPerson: "Егоров Евгений Сергеевич",
    city: "Архангельск",
    applicationStatus: "Ожидает",
  },
  {
    applicationNumber: 12568,
    applicationDate: "08.03.2025",
    contactPerson: "Козлова Диана Андреевна",
    city: "Пятигорск",
    applicationStatus: "Завершена",
  },
];