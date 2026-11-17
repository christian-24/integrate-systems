// Odczyt wydarzeń z kalendarza macOS przez EventKit.
// Kalendarz na Macu synchronizuje się z iCloud, więc to te same dane co w iPhonie.
// Tylko odczyt. Wynik: JSON na stdout albo do pliku (--out).
//
// Użycie: kalendarz [--back 1] [--ahead 30] [--out plik.json] [--summary] [--no-prompt]
import EventKit
import Foundation

let args = CommandLine.arguments
func arg(_ name: String, _ def: String) -> String {
    if let i = args.firstIndex(of: name), i + 1 < args.count { return args[i + 1] }
    return def
}
let back = Int(arg("--back", "1")) ?? 1
let ahead = Int(arg("--ahead", "30")) ?? 30
let outPath = arg("--out", "")
let summaryOnly = args.contains("--summary")
let noPrompt = args.contains("--no-prompt")  // nie pokazuj pytania o zgodę, tylko zgłoś stan

func emit(_ obj: [String: Any]) -> Never {
    let data = try! JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys])
    if outPath.isEmpty {
        FileHandle.standardOutput.write(data)
        print("")
    } else {
        try? data.write(to: URL(fileURLWithPath: outPath), options: .atomic)
    }
    exit(0)
}

let store = EKEventStore()
var status = EKEventStore.authorizationStatus(for: .event).rawValue
var reqError = ""
if status == 0 && !noPrompt {  // notDetermined: macOS pokaże pytanie o zgodę
    let sem = DispatchSemaphore(value: 0)
    if #available(macOS 14.0, *) {
        store.requestFullAccessToEvents { _, err in reqError = err?.localizedDescription ?? ""; sem.signal() }
    } else {
        store.requestAccess(to: .event) { _, err in reqError = err?.localizedDescription ?? ""; sem.signal() }
    }
    if sem.wait(timeout: .now() + 120) == .timedOut { reqError = "brak odpowiedzi na pytanie o zgodę (120 s)" }
    status = EKEventStore.authorizationStatus(for: .event).rawValue
}
// 3 = pełny dostęp. 0 brak decyzji, 1 ograniczony, 2 odmowa, 4 tylko zapis.
if status != 3 {
    let names = [0: "not_determined", 1: "restricted", 2: "denied", 4: "write_only"]
    emit(["status": names[status] ?? "unknown", "error": reqError])
}

func hex(_ c: CGColor?) -> String {
    guard let c = c, let srgb = CGColorSpace(name: CGColorSpace.sRGB),
          let k = c.converted(to: srgb, intent: .defaultIntent, options: nil),
          let p = k.components, p.count >= 3 else { return "#888888" }
    return String(format: "#%02x%02x%02x", Int(p[0] * 255), Int(p[1] * 255), Int(p[2] * 255))
}

let cal = Calendar.current
let today = cal.startOfDay(for: Date())
let from = cal.date(byAdding: .day, value: -back, to: today)!
let to = cal.date(byAdding: .day, value: ahead + 1, to: today)!
let calendars = store.calendars(for: .event)
let events = store.events(matching: store.predicateForEvents(withStart: from, end: to, calendars: nil))

if summaryOnly {
    emit(["status": "ok", "calendars": calendars.count, "events": events.count])
}

let dayFmt = DateFormatter()
dayFmt.locale = Locale(identifier: "en_US_POSIX")
dayFmt.dateFormat = "yyyy-MM-dd"
let timeFmt = DateFormatter()
timeFmt.locale = Locale(identifier: "en_US_POSIX")
timeFmt.dateFormat = "yyyy-MM-dd'T'HH:mm:ssXXX"

var outCals: [[String: Any]] = []
for c in calendars {
    outCals.append(["id": c.calendarIdentifier, "title": c.title, "color": hex(c.cgColor), "source": c.source?.title ?? ""])
}
var outEvents: [[String: Any]] = []
for e in events.sorted(by: { $0.startDate < $1.startDate }) {
    var item: [String: Any] = [
        "id": (e.eventIdentifier ?? UUID().uuidString) + "@" + dayFmt.string(from: e.startDate),
        "title": e.title ?? "",
        "allDay": e.isAllDay,
        "calendar": e.calendar?.title ?? "",
        "calendarId": e.calendar?.calendarIdentifier ?? "",
        "color": hex(e.calendar?.cgColor),
    ]
    if e.isAllDay {
        item["start"] = dayFmt.string(from: e.startDate)
        item["end"] = dayFmt.string(from: e.endDate)
    } else {
        item["start"] = timeFmt.string(from: e.startDate)
        item["end"] = timeFmt.string(from: e.endDate)
    }
    if let loc = e.location, !loc.isEmpty { item["location"] = loc }
    outEvents.append(item)
}
emit(["status": "ok", "calendars": outCals, "events": outEvents])
